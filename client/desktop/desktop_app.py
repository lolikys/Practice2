import tkinter as tk
from tkinter import ttk, messagebox
import requests
import json

API_URL = "http://localhost:8000/api"

class AcademiApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Academi Desktop")
        self.root.geometry("400x300")
        self.token = None
        self.show_login()

    def show_login(self):
        self.clear_window()
        tk.Label(self.root, text="Вход в систему", font=("Arial", 16)).pack(pady=20)
        
        tk.Label(self.root, text="Логин:").pack()
        self.username = tk.Entry(self.root)
        self.username.pack()
        
        tk.Label(self.root, text="Пароль:").pack()
        self.password = tk.Entry(self.root, show="*")
        self.password.pack()
        
        tk.Button(self.root, text="Войти", command=self.login).pack(pady=20)

    def login(self):
        u = self.username.get()
        p = self.password.get()
        try:
            res = requests.post(f"{API_URL}/login", json={"username": u, "password": p})
            if res.status_code == 200:
                self.token = res.json()["access_token"]
                self.show_courses()
            else:
                messagebox.showerror("Ошибка", "Неверный логин или пароль")
        except:
            messagebox.showerror("Ошибка", "Сервер API не запущен")

    def show_courses(self):
        self.clear_window()
        tk.Label(self.root, text="Мои курсы", font=("Arial", 16)).pack(pady=10)
        
        self.tree = ttk.Treeview(self.root, columns=("title", "duration"), show="headings")
        self.tree.heading("title", text="Название")
        self.tree.heading("duration", text="Длительность")
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10)
        
        headers = {"Authorization": f"Bearer {self.token}"}
        res = requests.get(f"{API_URL}/my-courses", headers=headers)
        courses = res.json()
        
        for c in courses:
            self.tree.insert("", tk.END, values=(c["title"], c["duration"]))
            
        tk.Button(self.root, text="Выйти", command=self.show_login).pack(pady=10)

    def clear_window(self):
        for widget in self.root.winfo_children():
            widget.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = AcademiApp(root)
    root.mainloop()