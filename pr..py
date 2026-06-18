import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk
from tkinter import messagebox, Label
from datetime import datetime


def save_and_plot():
    new_doxod = entry_doxod.get()
    new_day = entry_day.get()
    if not new_doxod or not new_day:
        messagebox.showwarning("Предупреждение", "Заполните оба поля!")
        return
    with open('res.txt', 'a', encoding='utf-8') as f:
        f.write(new_doxod + '\n')
        f.write(new_day + '\n')
    entry_doxod.delete(0, tk.END)
    entry_day.delete(0, tk.END)
    update_plot()


def update_plot():
    with open('res.txt', 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]
    doxod = []
    days = []
    for i in range(0, len(lines), 2):
        if i + 1 < len(lines):
            doxod.append(float(lines[i]))
            days.append(lines[i+1])
    if len(doxod) >= 2:
        prev = doxod[-2]
        curr = doxod[-1]
        change = curr - prev
        percent = (change / prev) * 100 if prev != 0 else 0
        if change > 0:
            trend = f"{change:.2f} руб (+{percent:.1f}%)"
        elif change < 0:
            trend = f" {change:.2f} руб ({percent:.1f}%)"
        else:
            trend = "Без изменений"
        label_result.config(text=f" ДО: {prev:.2f} руб\n ЩАС: {curr:.2f} руб\n{trend}")
    else:
        label_result.config(text=f"Первый доход: {doxod[-1]:.2f} руб\n Дата: {days[-1]}")
    for widget in frame_graph.winfo_children():
        widget.destroy()
    fig, ax = plt.subplots(figsize=(5, 3))
    ax.plot(days, doxod, marker='o', linewidth=2, markersize=8, color='green')
    ax.set_title("Динамика доходов", fontsize=12, fontweight='bold')
    ax.set_xlabel("Дата", fontsize=10)
    ax.set_ylabel("Доход (руб)", fontsize=10)
    ax.tick_params(axis='x', rotation=45)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    canvas = FigureCanvasTkAgg(fig, master=frame_graph)
    canvas.draw()
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    filename = f"graph_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    fig.savefig(filename, dpi=100, bbox_inches='tight')
    fig.savefig("last_graph.png", dpi=100, bbox_inches='tight')


root = tk.Tk()
root.title("Учёт доходов - До и Щас")
root.geometry("600x700")
root.configure(bg='#f0f0f0')
title_label = Label(root, text=" Учёт доходов ", font=("Arial", 16, "bold"), bg='#f0f0f0')
title_label.pack(pady=10)
label_doxod = Label(root, text="Доход (руб):", font=("Arial", 11), bg='#f0f0f0')
label_doxod.pack(pady=5)
entry_doxod = tk.Entry(root, font=("Arial", 11), width=25)
entry_doxod.pack(pady=5)
label_day = Label(root, text="Дата (например: 2024-01-01):", font=("Arial", 11), bg='#f0f0f0')
label_day.pack(pady=5)
entry_day = tk.Entry(root, font=("Arial", 11), width=25)
entry_day.pack(pady=5)
button_save = tk.Button(root, text=" Сохранить и показать график", command=save_and_plot,
                       bg='#4CAF50', fg='white', font=("Arial", 11, "bold"), padx=10, pady=5)
button_save.pack(pady=20)
label_result = Label(root, text="", font=("Arial", 11), bg='#f0f0f0', justify="left",
                    relief="solid", padx=10, pady=10)
label_result.pack(pady=10, padx=20, fill="both")
frame_graph = tk.Frame(root, bg='#f0f0f0', height=300)
frame_graph.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)
info_label = Label(root, text=" После каждого сохранения:\n Строится график всех доходов\n Картинка графика сохраняется\n Показывается сравнение с прошлым доходом",
                  font=("Arial", 9), bg='#f0f0f0', fg='#666', justify="left")
info_label.pack(pady=10)
root.mainloop()