import tkinter as tk

from tkinter import messagebox
from tkinter import simpledialog

class TodoApp:
    def __init__(self, root):
        self.root=root
        self.root.title("To-Do List App")
        self.root.geometry("500x400")
        self.root.resizable(False,False)
        self.root.configure(bg="#f0f0f0")

        self.todo_list=[]

        self.header=tk.Label(root,text="YAPILACAKLAR LİSTESİ",font=("Arial",16,"bold"),bg="#f0f0f0",fg="#333333")
        self.header.pack(pady=10)

        self.input_frame=tk.Frame(root,bg="#f0f0f0")
        self.input_frame.pack(pady=10)

        self.task_entry=tk.Entry(self.input_frame,width=30,font=("Arial",12),bd=2)
        self.task_entry.grid(row=0,column=0,padx=5)

        self.add_button=tk.Button(self.input_frame,text="Ekle",font=("Arial",12),command=self._ekle, bg="#4CAF50",fg="white",bd=0,width=10)
        self.add_button.grid(row=0,column=1,padx=5)

        self.task_frame = tk.Frame(root, bg="#f0f0f0")
        self.task_frame.pack(pady=10,fill=tk.BOTH,expand=True)

        self.task_listbox = tk.Listbox(self.task_frame, font=("Arial", 12), bd=2, selectbackground="#4CAF50", activestyle="none")
        self.task_listbox.pack(side=tk.LEFT,fill=tk.BOTH, padx=10, expand=True)

        self.scrollbar = tk.Scrollbar(self.task_frame)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.task_listbox.config(yscrollcommand=self.scrollbar.set)
        self.scrollbar.config(command=self.task_listbox.yview)

        self.button_frame = tk.Frame(root,bg="#f0f0f0")
        self.button_frame.pack(pady=10)

        self.clear_button = tk.Button(self.button_frame, text="Sil",command=self._sil, bg="#f44336",fg="white",font=("Arial",10,"bold"),width=8)
        self.clear_button.grid(row=0,column=0,padx=5)

        self.delete_button = tk.Button(self.button_frame, text="Hepsini Sil",command=self._hepsiniSil, bg="#f44336",fg="white",font=("Arial",10,"bold"),width=8)
        self.delete_button.grid(row=0,column=1,padx=5)

        self.exit_button = tk.Button(self.button_frame, text="Çıkış",command=root.destroy, bg="#f44336",fg="white",font=("Arial",10,"bold"),width=8)
        self.exit_button.grid(row=0,column=2,padx=5)

        self.task_entry.focus()

    def _ekle(self):
        gorev=self.task_entry.get().strip()

        if gorev:
            self.todo_list.append(gorev)

            self.task_listbox.insert(tk.END,f"{len(self.todo_list)}.{gorev}")
            self.task_entry.delete(0,tk.END)
        else:
            messagebox.showwarning("Uyarı", "GİRİŞ YOK")

    def _sil(self):
        try:
            selected_index=self.task_listbox.curselection()[0]
            self.task_listbox.delete(selected_index)
            self.todo_list.pop(selected_index)

            self.task_listbox.delete(0,tk.END)

            for idx, gorev in enumerate(self.todo_list,1):
                self.task_listbox.insert(tk.END,f"{idx}. {gorev}")
            
        except IndexError:
            messagebox.showwarning("Uyarı", "Silinecek Öğe Seçilmedi")

    def _hepsiniSil(self):
        if messagebox.askyesno("Onay","Tüm Görevleri Silmek İster Misiniz?"):
            self.task_listbox.delete(0,tk.END)
            self.todo_list.clear()

if __name__=="__main__":
    root=tk.Tk()
    app = TodoApp(root)
    root.mainloop()