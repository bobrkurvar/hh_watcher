import logging
import tkinter as tk
import webbrowser
from datetime import datetime
from queue import Empty, Queue
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText

from dto import Vacancy


log = logging.getLogger(__name__)


RELEVANT_MARK = 0
HIDDEN_MARK = 1


def format_published_at(value: str | datetime | None) -> str:
    if value is None:
        return "-"

    if isinstance(value, datetime):
        published_at = value
    else:
        try:
            published_at = datetime.fromisoformat(
                value.replace("Z", "+00:00"),
            )
        except (TypeError, ValueError):
            return str(value)

    return published_at.strftime("%d.%m.%Y %H:%M")


def format_salary(
    salary_from: int | None,
    salary_to: int | None,
    currency: str | None,
) -> str:
    if salary_from is None and salary_to is None:
        return "-"

    currency_text = {
        "RUR": "₽",
        "RUB": "₽",
        "USD": "$",
        "EUR": "€",
        "KZT": "₸",
        "BYR": "Br",
        "BYN": "Br",
    }.get(currency or "", currency or "")

    def format_amount(value: int) -> str:
        return f"{value:,}".replace(",", " ")

    if salary_from is not None and salary_to is not None:
        if salary_from == salary_to:
            salary = format_amount(salary_from)
        else:
            salary = (
                f"{format_amount(salary_from)} – "
                f"{format_amount(salary_to)}"
            )
    elif salary_from is not None:
        salary = f"от {format_amount(salary_from)}"
    else:
        salary = f"до {format_amount(salary_to)}"

    return f"{salary} {currency_text}".strip()


def vacancy_is_hidden(vacancy: Vacancy) -> bool:
    if hasattr(vacancy, "is_hidden"):
        return bool(vacancy.is_hidden)

    return bool(getattr(vacancy, "hidden", False))


def relevance_text(vacancy: Vacancy) -> str:
    if vacancy_is_hidden(vacancy):
        return "HIDDEN"

    if vacancy.ai_analysis is None:
        return "—"

    return "RELEVANT" if vacancy.ai_analysis.is_relevant else "HIDDEN"


def relevance_tag(vacancy: Vacancy) -> str:
    if vacancy_is_hidden(vacancy):
        return "hidden"

    if vacancy.ai_analysis is not None and vacancy.ai_analysis.is_relevant:
        return "relevant"

    return "unknown"


class App(tk.Tk):
    def __init__(self, backend):
        super().__init__()

        self.title("HH Watcher")
        self.geometry("1450x800")

        self.vacancies: list[Vacancy] = []
        self.selected_vacancy: Vacancy | None = None
        self.backend = backend
        self.callback_queue = Queue()
        self.is_closing = False

        self.create_widgets()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.after(50, self.process_callbacks)

    def enqueue_callback(self, callback, *args, **kwargs) -> None:
        self.callback_queue.put((callback, args, kwargs))

    def process_callbacks(self) -> None:
        if self.is_closing:
            return

        try:
            while True:
                callback, args, kwargs = self.callback_queue.get_nowait()
                callback(*args, **kwargs)
        except Empty:
            pass

        self.after(50, self.process_callbacks)

    def create_widgets(self) -> None:
        top_frame = ttk.Frame(self, padding=8)
        top_frame.pack(fill="x")

        self.load_button = ttk.Button(
            top_frame,
            text="Загрузить и обновить",
            command=self.start_loading,
        )
        self.load_button.pack(side="left")

        self.refresh_button = ttk.Button(
            top_frame,
            text="Прочитать из БД",
            command=self.start_reading_vacancies,
        )
        self.refresh_button.pack(side="left", padx=(8, 0))

        self.open_button = ttk.Button(
            top_frame,
            text="Открыть в браузере",
            command=self.open_selected_vacancy,
            state="disabled",
        )
        self.open_button.pack(side="left", padx=(8, 0))

        self.status_label = ttk.Label(
            top_frame,
            text="Готово",
        )
        self.status_label.pack(side="left", padx=(12, 0))

        paned = ttk.Panedwindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill="both", expand=True, padx=8, pady=8)

        self.create_vacancies_panel(paned)
        self.create_details_panel(paned)

    def create_vacancies_panel(self, paned: ttk.Panedwindow) -> None:
        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=1)

        ttk.Label(
            left_frame,
            text="Активные вакансии",
        ).pack(anchor="w", pady=(0, 6))

        tree_frame = ttk.Frame(left_frame)
        tree_frame.pack(fill="both", expand=True)
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        columns = (
            "relevance",
            "title",
            "employer",
            "experience",
            "salary",
            "queries",
        )

        self.tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="headings",
            height=25,
        )

        self.tree.tag_configure("relevant", background="#eaf7ea")
        self.tree.tag_configure("unknown", background="#f2f2f2")
        self.tree.tag_configure("hidden", foreground="#999999")

        self.tree.heading("relevance", text="Результат")
        self.tree.heading("title", text="Название")
        self.tree.heading("employer", text="Компания")
        self.tree.heading("experience", text="Опыт")
        self.tree.heading("salary", text="Зарплата")
        self.tree.heading("queries", text="Запросы")

        self.tree.column("relevance", width=95, anchor="center")
        self.tree.column("title", width=350, anchor="w")
        self.tree.column("employer", width=190, anchor="w")
        self.tree.column("experience", width=145, anchor="w")
        self.tree.column("salary", width=145, anchor="w")
        self.tree.column("queries", width=210, anchor="w")

        tree_scroll_y = ttk.Scrollbar(
            tree_frame,
            orient="vertical",
            command=self.tree.yview,
        )
        tree_scroll_x = ttk.Scrollbar(
            tree_frame,
            orient="horizontal",
            command=self.tree.xview,
        )

        self.tree.configure(
            yscrollcommand=tree_scroll_y.set,
            xscrollcommand=tree_scroll_x.set,
        )

        self.tree.grid(row=0, column=0, sticky="nsew")
        tree_scroll_y.grid(row=0, column=1, sticky="ns")
        tree_scroll_x.grid(row=1, column=0, sticky="ew")

        self.tree.bind(
            "<<TreeviewSelect>>",
            self.on_vacancy_select,
        )

    def create_details_panel(self, paned: ttk.Panedwindow) -> None:
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=2)

        ttk.Label(
            right_frame,
            text="Детали вакансии",
        ).pack(anchor="w", pady=(0, 6))

        info_frame = ttk.Frame(right_frame)
        info_frame.pack(fill="x", pady=(0, 8))

        self.title_var = tk.StringVar(value="Название: ")
        self.employer_var = tk.StringVar(value="Компания: ")
        self.published_at_var = tk.StringVar(value="Опубликовано: ")
        self.queries_var = tk.StringVar(value="Найдена по запросам: ")
        self.salary_var = tk.StringVar(value="Зарплата: ")
        self.experience_var = tk.StringVar(value="Опыт: ")
        self.employment_var = tk.StringVar(value="Занятость: ")
        self.schedule_var = tk.StringVar(value="График: ")
        self.work_formats_var = tk.StringVar(value="Формат работы: ")
        self.skills_var = tk.StringVar(value="Навыки: ")
        self.url_var = tk.StringVar(value="Ссылка: ")

        ttk.Label(
            info_frame,
            textvariable=self.title_var,
            font=("Segoe UI", 10, "bold"),
            wraplength=700,
        ).pack(anchor="w", pady=2)

        for variable in (
            self.employer_var,
            self.published_at_var,
            self.queries_var,
            self.salary_var,
            self.experience_var,
            self.employment_var,
            self.schedule_var,
            self.work_formats_var,
            self.skills_var,
        ):
            ttk.Label(
                info_frame,
                textvariable=variable,
                wraplength=700,
            ).pack(anchor="w", pady=2)

        self.url_label = ttk.Label(
            info_frame,
            textvariable=self.url_var,
            foreground="blue",
            cursor="hand2",
        )
        self.url_label.pack(anchor="w", pady=2)
        self.url_label.bind(
            "<Button-1>",
            lambda _event: self.open_selected_vacancy(),
        )

        self.create_mark_frame(right_frame)

        ttk.Label(
            right_frame,
            text="Описание",
        ).pack(anchor="w", pady=(6, 4))

        self.details_text = ScrolledText(
            right_frame,
            wrap="word",
            font=("Consolas", 10),
        )
        self.details_text.pack(fill="both", expand=True)

    def create_mark_frame(self, parent: ttk.Frame) -> None:
        self.mark_frame = ttk.LabelFrame(
            parent,
            text="Разметка для обучения",
        )
        self.mark_frame.pack(fill="x", pady=(8, 8), padx=4)

        self.mark_var = tk.IntVar(value=-1)

        rb_frame = ttk.Frame(self.mark_frame)
        rb_frame.pack(
            anchor="w",
            fill="x",
            padx=5,
            pady=4,
        )

        ttk.Radiobutton(
            rb_frame,
            text="RELEVANT (0)",
            variable=self.mark_var,
            value=RELEVANT_MARK,
        ).pack(side="left", padx=(0, 10))

        ttk.Radiobutton(
            rb_frame,
            text="HIDDEN (1)",
            variable=self.mark_var,
            value=HIDDEN_MARK,
        ).pack(side="left", padx=10)

        button_frame = ttk.Frame(self.mark_frame)
        button_frame.pack(
            anchor="w",
            fill="x",
            padx=5,
            pady=(0, 6),
        )

        self.save_mark_btn = ttk.Button(
            button_frame,
            text="Сохранить оценку",
            command=self.save_human_mark,
            state="disabled",
        )
        self.save_mark_btn.pack(side="left")

        self.mark_status = ttk.Label(
            button_frame,
            text="",
            font=("Segoe UI", 9, "bold"),
        )
        self.mark_status.pack(side="left", padx=10)

    def start_loading(self) -> None:
        self.set_loading_state("Поиск и анализ новых вакансий...")
        self.clear_ui()

        self.backend.load_vacancies(
            callback=lambda result: self.enqueue_callback(
                self.on_loading_complete,
                result,
            ),
        )

    def start_reading_vacancies(self) -> None:
        self.set_loading_state("Чтение вакансий из БД...")
        self.clear_ui()

        self.backend.read_vacancies(
            callback=lambda result: self.enqueue_callback(
                self.on_loading_complete,
                result,
            ),
        )

    def set_loading_state(self, text: str) -> None:
        self.load_button.config(state="disabled")
        self.refresh_button.config(state="disabled")
        self.open_button.config(state="disabled")
        self.status_label.config(text=text)

    def on_loading_complete(self, result) -> None:
        if isinstance(result, Exception):
            self.show_error(result)
            return

        self.show_result(result)

    def clear_ui(self) -> None:
        self.vacancies = []

        for item_id in self.tree.get_children():
            self.tree.delete(item_id)

        self.clear_details_panel()

    def clear_details_panel(self) -> None:
        self.selected_vacancy = None

        self.title_var.set("Название: ")
        self.employer_var.set("Компания: ")
        self.published_at_var.set("Опубликовано: ")
        self.queries_var.set("Найдена по запросам: ")
        self.salary_var.set("Зарплата: ")
        self.experience_var.set("Опыт: ")
        self.employment_var.set("Занятость: ")
        self.schedule_var.set("График: ")
        self.work_formats_var.set("Формат работы: ")
        self.skills_var.set("Навыки: ")
        self.url_var.set("Ссылка: ")

        self.details_text.delete("1.0", tk.END)

        self.mark_var.set(-1)
        self.save_mark_btn.config(state="disabled")
        self.mark_status.config(text="", foreground="black")
        self.open_button.config(state="disabled")

    def show_result(self, vacancies: list[Vacancy]) -> None:
        self.vacancies = list(vacancies)

        for index, vacancy in enumerate(self.vacancies):
            preview = vacancy.preview
            details = vacancy.details

            salary_text = "-"
            experience_text = "-"

            if details is not None:
                salary_text = format_salary(
                    details.salary_from,
                    details.salary_to,
                    details.salary_currency,
                )
                experience_text = details.experience or "-"

            queries_text = (
                ", ".join(sorted(preview.query_hits))
                if preview.query_hits
                else "-"
            )

            self.tree.insert(
                "",
                "end",
                iid=str(index),
                values=(
                    relevance_text(vacancy),
                    preview.title,
                    preview.employer_name or "-",
                    experience_text,
                    salary_text,
                    queries_text,
                ),
                tags=(relevance_tag(vacancy),),
            )

        self.status_label.config(
            text=f"Готово. Вакансий: {len(self.vacancies)}",
        )
        self.load_button.config(state="normal")
        self.refresh_button.config(state="normal")

        if not self.vacancies:
            return

        first_id = self.tree.get_children()[0]
        self.tree.selection_set(first_id)
        self.tree.focus(first_id)
        self.on_vacancy_select(None)

    def on_vacancy_select(self, _event) -> None:
        selected = self.tree.selection()
        if not selected:
            return

        item_id = selected[0]
        vacancy = self.vacancies[int(item_id)]
        preview = vacancy.preview
        details = vacancy.details
        ai = vacancy.ai_analysis

        self.selected_vacancy = vacancy

        self.title_var.set(f"Название: {preview.title}")
        self.employer_var.set(f"Компания: {preview.employer_name or '-'}")
        self.published_at_var.set(
            f"Опубликовано: {format_published_at(preview.published_at)}",
        )
        self.queries_var.set(
            "Найдена по запросам: "
            + (
                ", ".join(sorted(preview.query_hits))
                if preview.query_hits
                else "-"
            ),
        )
        self.url_var.set(f"Ссылка: {preview.url}")

        if details is None:
            self.salary_var.set("Зарплата: -")
            self.experience_var.set("Опыт: -")
            self.employment_var.set("Занятость: -")
            self.schedule_var.set("График: -")
            self.work_formats_var.set("Формат работы: -")
            self.skills_var.set("Навыки: -")
        else:
            self.salary_var.set(
                "Зарплата: "
                + format_salary(
                    details.salary_from,
                    details.salary_to,
                    details.salary_currency,
                ),
            )
            self.experience_var.set(f"Опыт: {details.experience or '-'}")
            self.employment_var.set(
                f"Занятость: {details.employment or '-'}",
            )
            self.schedule_var.set(f"График: {details.schedule or '-'}")
            self.work_formats_var.set(
                "Формат работы: "
                + (
                    ", ".join(details.work_formats)
                    if details.work_formats
                    else "-"
                ),
            )
            self.skills_var.set(
                "Навыки: "
                + (
                    ", ".join(details.key_skills)
                    if details.key_skills
                    else "-"
                ),
            )

        self.mark_var.set(
            HIDDEN_MARK if vacancy_is_hidden(vacancy) else RELEVANT_MARK,
        )
        self.save_mark_btn.config(state="normal")
        self.mark_status.config(text="", foreground="black")

        self.details_text.delete("1.0", tk.END)

        if ai is not None:
            self.details_text.insert(
                tk.END,
                "Вердикт ИИ: "
                f"{'RELEVANT' if ai.is_relevant else 'HIDDEN'}\n",
            )
            self.details_text.insert(
                tk.END,
                f"Уверенность ИИ: {ai.confidence:.0%}\n",
            )
            self.details_text.insert(
                tk.END,
                f"Объяснение ИИ: {ai.explanation or '-'}\n\n",
            )

        if preview.requirement:
            self.details_text.insert(
                tk.END,
                f"Требования из выдачи:\n{preview.requirement}\n\n",
            )

        if preview.responsibility:
            self.details_text.insert(
                tk.END,
                f"Обязанности из выдачи:\n{preview.responsibility}\n\n",
            )

        if details is not None:
            self.details_text.insert(tk.END, details.description)
        else:
            self.details_text.insert(
                tk.END,
                "Полное описание вакансии не загружалось.",
            )

        self.open_button.config(state="normal")

    def save_human_mark(self) -> None:
        if self.selected_vacancy is None:
            return

        mark_value = self.mark_var.get()
        if mark_value == -1:
            return

        if self.selected_vacancy.id is None:
            self.mark_status.config(
                text="Ошибка: нет ID записи",
                foreground="red",
            )
            return

        selected = self.tree.selection()
        if not selected:
            return

        item_id = selected[0]
        hidden = mark_value == HIDDEN_MARK

        self.save_mark_btn.config(state="disabled")
        self.mark_status.config(
            text="Сохранение...",
            foreground="black",
        )

        self.backend.update_hidden(
            vacancy_id=self.selected_vacancy.id,
            hidden=hidden,
            callback=lambda result: self.enqueue_callback(
                self.on_mark_saved,
                result,
                item_id,
                hidden,
            ),
        )

    def on_mark_saved(
        self,
        result,
        item_id: str,
        hidden: bool,
    ) -> None:
        if isinstance(result, Exception):
            self.save_mark_btn.config(state="normal")
            self.mark_status.config(
                text="Ошибка БД",
                foreground="red",
            )
            log.error(
                "Ошибка сохранения разметки: %s",
                result,
                exc_info=result,
            )
            return

        vacancy = self.vacancies[int(item_id)]

        if hasattr(vacancy, "is_hidden"):
            vacancy.is_hidden = hidden
        else:
            vacancy.hidden = hidden

        self.tree.set(
            item_id,
            "relevance",
            relevance_text(vacancy),
        )
        self.tree.item(
            item_id,
            tags=(relevance_tag(vacancy),),
        )

        self.save_mark_btn.config(state="normal")
        self.mark_status.config(
            text="Сохранено",
            foreground="green",
        )

    def open_selected_vacancy(self) -> None:
        if self.selected_vacancy is None:
            return

        url = self.selected_vacancy.preview.url
        if url:
            webbrowser.open(url)

    def show_error(self, error: Exception) -> None:
        self.status_label.config(text="Ошибка")
        self.load_button.config(state="normal")
        self.refresh_button.config(state="normal")
        self.open_button.config(state="disabled")

        self.details_text.delete("1.0", tk.END)
        self.details_text.insert(
            "1.0",
            f"Ошибка при загрузке вакансий:\n\n{error}",
        )

        log.error(
            "Ошибка загрузки: %s",
            error,
            exc_info=error,
        )

    def on_close(self) -> None:
        self.is_closing = True

        try:
            self.backend.stop()
        finally:
            self.destroy()