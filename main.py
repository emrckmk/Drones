import asyncio
import time
import cv2
import numpy as np
from mavsdk import System
from mavsdk.offboard import OffboardError, VelocityBodyYawspeed


# ---------------------------
# HSV yardımcıları
# ---------------------------
def clip(a, lo, hi):
    return np.array([max(lo[i], min(hi[i], a[i])) for i in range(3)], dtype=np.uint8)


def build_hsv_ranges_from_pixel(hsv_pixel, tol_h=12, tol_s=60, tol_v=60):
    h, s, v = int(hsv_pixel[0]), int(hsv_pixel[1]), int(hsv_pixel[2])
    low = clip(np.array([h - tol_h, s - tol_s, v - tol_v]), [0, 0, 0], [179, 255, 255])
    high = clip(np.array([h + tol_h, s + tol_s, v + tol_v]), [0, 0, 0], [179, 255, 255])

    if low[0] <= high[0]:
        return [(low, high)]
    r1 = (
        np.array([0, low[1], low[2]], dtype=np.uint8),
        np.array([high[0], high[1], high[2]], dtype=np.uint8),
    )
    r2 = (
        np.array([low[0], low[1], low[2]], dtype=np.uint8),
        np.array([179, high[1], high[2]], dtype=np.uint8),
    )
    return [r1, r2]


def make_mask(hsv_frame, ranges):
    mask = None
    for lo, hi in ranges:
        part = cv2.inRange(hsv_frame, lo, hi)
        mask = part if mask is None else cv2.bitwise_or(mask, part)
    return mask if mask is not None else np.zeros(hsv_frame.shape[:2], dtype=np.uint8)


# --- Maske iyileştirme + en büyük kutu seçimi (renkle yeniden-bulma için) ---
def clean_mask(mask):
    k_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    k_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k_open, iterations=1)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k_close, iterations=1)
    return mask


def largest_box_from_mask(mask, min_area_ratio=0.0005, min_solidity=0.6):
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return None
    h, w = mask.shape[:2]
    best, best_area = None, 0.0
    for c in cnts:
        area = cv2.contourArea(c)
        if area < min_area_ratio * (h * w):
            continue
        hull = cv2.convexHull(c)
        hull_area = cv2.contourArea(hull)
        if hull_area <= 1e-6 or (area / hull_area) < min_solidity:
            continue
        x, y, bw, bh = cv2.boundingRect(c)
        if area > best_area:
            best_area, best = area, (x, y, bw, bh)
    return best


def refine_bbox_with_mask(frame_bgr, bbox, ranges, scale=1.4):
    """Maskeyi kullanarak kutuyu yerel ROI içinde iyileştir."""
    if bbox is None:
        return None, None

    x, y, w, h = bbox
    if w <= 0 or h <= 0:
        return None, None

    H, W = frame_bgr.shape[:2]
    size = int(max(w, h) * scale)
    cx, cy = x + w // 2, y + h // 2
    x0 = max(0, cx - size // 2)
    y0 = max(0, cy - size // 2)
    x1 = min(W, x0 + size)
    y1 = min(H, y0 + size)
    roi = frame_bgr[y0:y1, x0:x1]
    if roi.size == 0:
        return None, None

    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    mask = clean_mask(make_mask(hsv, ranges))
    box = largest_box_from_mask(mask, min_area_ratio=0.002)
    if box is None:
        return None, mask

    rx, ry, rw, rh = box
    refined = (x0 + rx, y0 + ry, rw, rh)
    return refined, mask


# --- Tracker yardımcıları ---
def create_tracker():
    # CSRT -> yoksa KCF fallback
    if hasattr(cv2, "legacy") and hasattr(cv2.legacy, "TrackerCSRT_create"):
        return cv2.legacy.TrackerCSRT_create()
    if hasattr(cv2, "TrackerCSRT_create"):
        return cv2.TrackerCSRT_create()
    if hasattr(cv2, "legacy") and hasattr(cv2.legacy, "TrackerKCF_create"):
        return cv2.legacy.TrackerKCF_create()
    if hasattr(cv2, "TrackerKCF_create"):
        return cv2.TrackerKCF_create()
    return None


def iou(a, b):
    ax1, ay1, aw, ah = a
    ax2, ay2 = ax1 + aw, ay1 + ah
    bx1, by1, bw, bh = b
    bx2, by2 = bx1 + bw, by1 + bh
    inter_w = max(0, min(ax2, bx2) - max(ax1, bx1))
    inter_h = max(0, min(ay2, by2) - max(ay1, by1))
    inter = inter_w * inter_h
    union = aw * ah + bw * bh - inter
    return inter / union if union > 0 else 0.0


# ROI ortalamasından HSV daraltma (maske kararlılığı için)
def tighten_hsv_by_roi(frame_bgr, bbox, cur_ranges, tol_h=8, tol_s=40, tol_v=40):
    cx, cy, w, h = bbox
    x0 = max(0, cx - w // 2)
    y0 = max(0, cy - h // 2)
    H, W = frame_bgr.shape[:2]
    x0 = min(W - 1, x0)
    y0 = min(H - 1, y0)
    w = max(1, min(W - x0, w))
    h = max(1, min(H - y0, h))
    roi = frame_bgr[y0 : y0 + h, x0 : x0 + w]
    if roi.size == 0:
        return cur_ranges
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    mean = np.mean(hsv.reshape(-1, 3), axis=0).astype(np.uint8)
    return build_hsv_ranges_from_pixel(mean, tol_h=tol_h, tol_s=tol_s, tol_v=tol_v)


# Telemetri irtifa izleyici
async def altitude_updater(drone, holder):
    async for pos in drone.telemetry.position():
        holder["alt"] = pos.relative_altitude_m


def update_search_state(state, active, yaw_rate):
    """Hedef kaybolduğunda 360° tarama için durum makinesi."""
    now = time.monotonic()
    if active:
        if not state["active"]:
            state.update({"active": True, "last_ts": now, "angle": 0.0, "dir": 1})
        dt = now - state.get("last_ts", now)
        state["last_ts"] = now
        state["angle"] += yaw_rate * dt
        if state["angle"] >= 360.0:
            state["angle"] = 0.0
            state["dir"] *= -1  # ters yönde bir tur daha at
        return state["dir"] * yaw_rate
    state.update({"active": False, "last_ts": now, "angle": 0.0, "dir": 1})
    return 0.0


async def fly_tracker():
    # 1) Bağlan
    drone = System()
    await drone.connect(system_address="udp://:14540")
    async for s in drone.core.connection_state():
        if s.is_connected:
            print("[OK] Connected")
            break

    # 2) Sağlık/konum
    print("[INFO] Waiting for position/home...")
    async for h in drone.telemetry.health():
        if h.is_global_position_ok and h.is_home_position_ok:
            print("[OK] Health good")
            break

    # 3) Arm + Takeoff
    await drone.action.arm()
    await drone.action.set_takeoff_altitude(3.0)
    await drone.action.takeoff()

    # 4) Kalkışı doğrula
    print("[INFO] Climbing to ~3m...")
    async for pos in drone.telemetry.position():
        if pos.relative_altitude_m >= 2.5:
            print("[OK] Takeoff reached (~3m)")
            break

    # 5) Offboard hazırlık
    await drone.offboard.set_velocity_body(VelocityBodyYawspeed(0.0, 0.0, 0.0, 0.0))
    await drone.offboard.start()
    print("[OK] Offboard")

    # 6) Kamera
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[ERR] Kamera yok")
        await drone.offboard.stop()
        await drone.action.land()
        return

    # Varsayılan kırmızı (iki aralık)
    hsv_ranges = [
        (np.array([0, 120, 70], dtype=np.uint8), np.array([10, 255, 255], dtype=np.uint8)),
        (np.array([170, 120, 70], dtype=np.uint8), np.array([179, 255, 255], dtype=np.uint8)),
    ]
    picked = False
    a_ref = None  # hedef alan referansı (normalize)
    a_lp = None  # alan için low-pass
    last_frame_bgr = [None]

    # ---- Takip durumları ----
    tracker = None
    has_track = False
    track_bbox = None  # (x,y,w,h)
    last_good = None
    prev_center = None
    lost_frames = 0
    MAX_GRACE = 15
    REDETECT_PERIOD = 10
    GATE_RATIO = 0.30
    auto_tighten_on = True
    frame_count = 0
    tighten_period = 20
    search_state = {"active": False, "last_ts": time.monotonic(), "angle": 0.0, "dir": 1}
    SEARCH_YAW_RATE = 25.0  # deg/s

    def on_mouse(event, x, y, flags, userdata):
        nonlocal hsv_ranges, picked, a_ref, tracker, has_track, track_bbox, last_good, prev_center, lost_frames
        if event == cv2.EVENT_LBUTTONDOWN and last_frame_bgr[0] is not None:
            H, W = last_frame_bgr[0].shape[:2]
            r = 10
            x0, y0 = max(0, x - r), max(0, y - r)
            x1, y1 = min(W, x + r + 1), min(H, y + r + 1)
            roi = last_frame_bgr[0][y0:y1, x0:x1]
            hsv_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
            px = hsv_roi.reshape(-1, 3).mean(axis=0).astype(np.uint8)
            hsv_ranges = build_hsv_ranges_from_pixel(px, tol_h=12, tol_s=60, tol_v=60)
            picked = True
            a_ref = None
            w_box = h_box = 80
            x_b = max(0, min(W - w_box, x - w_box // 2))
            y_b = max(0, min(H - h_box, y - h_box // 2))
            tracker = create_tracker()
            has_track = False
            if tracker is not None and tracker.init(last_frame_bgr[0], (x_b, y_b, w_box, h_box)):
                has_track = True
                track_bbox = (x_b, y_b, w_box, h_box)
                last_good = track_bbox
                prev_center = (x, y)
                lost_frames = 0
                print(f"[LOCK] Tracker init {(x_b, y_b, w_box, h_box)} | HSV={hsv_ranges}")
            else:
                print("[WARN] Tracker init failed (opencv-contrib gerekir). Renk tespitiyle devam.")

    win = "frame"
    cv2.namedWindow(win)
    cv2.setMouseCallback(win, on_mouse)

    # ---- Kontrol parametreleri ----
    Kp_xy = 1.2
    vmax_xy = 0.8
    dead_xy = 0.02

    Kp_z = 1.0
    vmax_z = 0.5
    dead_z = 0.02

    Kp_dist = 3.0
    vmax_x = 0.8
    vmin_x = 0.20
    dead_a = 0.0008

    alt_holder = {"alt": None}
    alt_task = asyncio.create_task(altitude_updater(drone, alt_holder))
    min_alt = 0.7
    max_alt = 8.0

    last_mask_vis = None

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frame_count += 1
            last_frame_bgr[0] = frame

            h, w = frame.shape[:2]
            cx_img, cy_img = w // 2, h // 2
            cv2.circle(frame, (cx_img, cy_img), 5, (255, 255, 255), -1)

            # ---------- Hedef ALGILAMA ----------
            show_bbox = None
            mask = None

            if has_track and tracker is not None:
                ok, box = tracker.update(frame)
                if ok:
                    track_bbox = tuple(map(int, box))
                    last_good = track_bbox
                    lost_frames = 0
                    show_bbox = track_bbox
                else:
                    has_track = False
                    lost_frames += 1

            if (not has_track) and picked and (frame_count % REDETECT_PERIOD == 0):
                blurred = cv2.GaussianBlur(frame, (5, 5), 0)
                hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)
                mask_raw = make_mask(hsv, hsv_ranges)
                mask = clean_mask(mask_raw)
                box = largest_box_from_mask(mask)
                if box is not None:
                    accept = True
                    if last_good is not None:
                        iou_val = iou(box, last_good)
                        bx, by, bw, bh = box
                        bc = (bx + bw // 2, by + bh // 2)
                        if prev_center is not None:
                            dx, dy = bc[0] - prev_center[0], bc[1] - prev_center[1]
                            dist = (dx * dx + dy * dy) ** 0.5
                            gate = GATE_RATIO * ((h ** 2 + w ** 2) ** 0.5)
                            if dist > gate and iou_val < 0.05:
                                accept = False
                    if accept:
                        tracker = create_tracker()
                        if tracker is not None and tracker.init(frame, box):
                            track_bbox = box
                            has_track = True
                            lost_frames = 0
                            last_good = box
                            show_bbox = box
                            print("[INFO] Re-detected and re-initialized tracker.")

            if show_bbox is None and last_good is not None and 0 < lost_frames <= MAX_GRACE:
                show_bbox = last_good

            if show_bbox is not None and picked:
                refined, roi_mask = refine_bbox_with_mask(frame, show_bbox, hsv_ranges)
                if refined is not None:
                    show_bbox = refined
                    track_bbox = refined
                    last_good = refined
                    last_mask_vis = roi_mask
                elif roi_mask is not None:
                    last_mask_vis = roi_mask

            if show_bbox is None:
                vx = vy = vz = 0.0
                a_err = None
                yawspeed = update_search_state(search_state, True, SEARCH_YAW_RATE)
                cv2.putText(
                    frame,
                    "No target (click to lock color/target)",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 0, 255),
                    2,
                )
            else:
                yawspeed = update_search_state(search_state, False, SEARCH_YAW_RATE)
                x, y, tw, th = show_bbox
                cx, cy = x + tw // 2, y + th // 2
                prev_center = (cx, cy)

                err_x = (cx - cx_img) / w
                err_y = (cy - cy_img) / h

                vy = 0.0
                if abs(err_x) >= dead_xy:
                    vy = float(np.clip(Kp_xy * err_x, -vmax_xy, vmax_xy))

                vz = 0.0
                if abs(err_y) >= dead_z:
                    vz = float(np.clip(Kp_z * err_y, -vmax_z, vmax_z))

                a_cur = (tw * th) / float(w * h)
                if a_lp is None:
                    a_lp = a_cur
                else:
                    a_lp = 0.8 * a_lp + 0.2 * a_cur

                if a_ref is None:
                    a_ref = a_lp
                    print(f"[REF] a_ref set to {a_ref:.5f}")

                a_err = (a_ref - a_lp)

                if abs(a_err) >= dead_a:
                    cmd_v = Kp_dist * a_err
                    mag = max(vmin_x, abs(cmd_v))
                    vx = float(np.clip(np.sign(cmd_v) * mag, -vmax_x, vmax_x))
                else:
                    vx = 0.0

                alt = alt_holder["alt"]
                if alt is not None:
                    if alt <= min_alt and vz > 0.0:
                        vz = 0.0
                    if alt >= max_alt and vz < 0.0:
                        vz = 0.0

                cv2.rectangle(frame, (x, y), (x + tw, y + th), (0, 255, 0), 2)
                cv2.circle(frame, (cx, cy), 5, (0, 255, 0), -1)
                cv2.putText(
                    frame,
                    f"vx={vx:.2f} vy={vy:.2f} vz={vz:.2f} yaw={yawspeed:.1f}",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 0),
                    2,
                )

                if auto_tighten_on and (frame_count % tighten_period == 0):
                    hsv_ranges = tighten_hsv_by_roi(frame, (cx, cy, tw, th), hsv_ranges)

                try:
                    await drone.offboard.set_velocity_body(
                        VelocityBodyYawspeed(vx, vy, vz, yawspeed)
                    )
                except OffboardError as err:
                    print(f"[ERR] Offboard command failed: {err}")

            mode = "LOCKED" if picked else "DEFAULT-RED"
            alt_txt = (
                f"alt={alt_holder['alt']:.2f}m" if alt_holder["alt"] is not None else "alt=?"
            )
            cv2.putText(
                frame,
                f"Mode: {mode} | {alt_txt}",
                (10, 90),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (200, 200, 200),
                2,
            )

            if a_lp is not None and a_ref is not None:
                a_err_txt = f"{a_err:.4f}" if a_err is not None else "None"
                cv2.putText(
                    frame,
                    f"a_lp={a_lp:.4f} a_ref={a_ref:.4f} a_err={a_err_txt}",
                    (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 255, 0),
                    2,
                )

            cv2.imshow(win, frame)

            if mask is not None:
                last_mask_vis = mask
            if last_mask_vis is not None:
                cv2.imshow("mask", last_mask_vis)

            key = cv2.waitKey(1) & 0xFF
            if key == 27:
                break
            elif key in (ord("r"), ord("R")) and a_lp is not None:
                a_ref = a_lp
                print(f"[REF] reset a_ref -> {a_ref:.5f}")
            elif key in (ord("t"), ord("T")):
                auto_tighten_on = not auto_tighten_on
                print(f"[HSV] auto-tighten = {auto_tighten_on}")

            if show_bbox is None:
                try:
                    yawspeed = update_search_state(search_state, True, SEARCH_YAW_RATE)
                    await drone.offboard.set_velocity_body(
                        VelocityBodyYawspeed(0.0, 0.0, 0.0, yawspeed)
                    )
                except OffboardError as err:
                    print(f"[ERR] Offboard hover failed: {err}")

    finally:
        cap.release()
        cv2.destroyAllWindows()
        try:
            await drone.offboard.set_velocity_body(VelocityBodyYawspeed(0, 0, 0, 0))
            await asyncio.sleep(0.5)
            await drone.offboard.stop()
        except Exception as e:
            print("[WARN] Offboard stop:", e)
        await drone.action.land()
        print("[DONE] Landed")
        try:
            alt_task.cancel()
        except Exception:
            pass


if __name__ == "__main__":
    asyncio.run(fly_tracker())
