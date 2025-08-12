import customtkinter as ctk # type: ignore

bar: ctk.CTkProgressBar

def init(progress_bar: ctk.CTkProgressBar) -> None:
    """Initializes the progress bar frame."""
    global bar
    bar = progress_bar

def show() -> None:
    """Shows the progress bar frame."""
    global bar
    bar.set(0)
    bar.configure(mode="determinate")
    # Re-grid the progress frame to make it visible
    bar.grid() # sticky="ew" to expand horizontally
    # window.update_idletasks() # Force UI update immediately

def hide() -> None:
    """Hides the progress bar frame."""
    global bar
    bar.grid_forget()
    bar.stop()

def update(value: float) -> None:
    """Updates the progress bar value (0.0 to 1.0) and sets mode to determinate."""
    global bar
    bar.set(value)

def show_indeterminate() -> None:
    """Sets the progress bar to indeterminate mode (activity indicator)."""
    global bar
    show()
    bar.configure(mode="indeterminate")
    bar.start()
