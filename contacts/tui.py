from textual.app import App, on
from textual.containers import Grid, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import (
    Button,
    DataTable, 
    Footer, 
    Header, 
    Input,
    Label,
    Static,
)


class ContactsApp(App):
    CSS_PATH = "contacts.tcss"
    BINDINGS = [
        ("m", "toggle_dark", "Toggle dark mode"),
        ("a", "add", "Add"),
        ("d", "delete", "Delete"),
        ("q", "request_quit", "Quit"),
        ("e", "edit", "Edit"),
        ("f", "sort_by_first_name", "Sort By First Name"),
        ("l", "sort_by_last_name", "Sort By Last Name"),

    ]

    def __init__(self, db):
        super().__init__()
        self.db = db

    current_sorts: set = set()


    def compose(self):
        global keys
        yield Header()
        contacts_list = DataTable(classes="contacts-list")
        contacts_list.focus()
        keys = contacts_list.add_columns("Name", "Phone", "Email")
        contacts_list.cursor_type = "row"
        contacts_list.zebra_stripes = True
        add_button = Button("Add", variant="success", id="add")
        add_button.focus()
        buttons_panel = Vertical(
            add_button,
            Button("Edit", variant="primary", id="edit"),  # Add Edit button here
            Button("Delete", variant="warning", id="delete"),
            Static(classes="separator"),
            Button("Clear All", variant="error", id="clear"),
            classes="buttons-panel"
        )
        yield Horizontal(contacts_list, buttons_panel)
        yield Footer()



    def on_mount(self):
        self.title = "Contacts"
        self._load_contacts()

    def sort_reverse(self, sort_type: str):
        """Determine if `sort_type` is ascending or descending."""
        reverse = sort_type in self.current_sorts
        if reverse:
            self.current_sorts.remove(sort_type)
        else:
            self.current_sorts.add(sort_type)

        return reverse
    
    def action_sort_by_last_name(self) -> None:
        """Sort DataTable by last name (via a lambda)."""
        table = self.query_one(DataTable)
        table.sort(
            keys[0],
            key=lambda name: (name.split()[-1], name.split()[0]),
            reverse=self.sort_reverse("name"),
        )

    def action_sort_by_first_name(self) -> None:
        """Sort DataTable by first name (via a lambda)."""
        table = self.query_one(DataTable)
        table.sort(
            keys[0],
            key=lambda name: (name.split()[0], name.split()[-1]),
            reverse=self.sort_reverse("name"),
        )

    def _load_contacts(self):
        contacts_list = self.query_one(DataTable)
        for contact_data in self.db.get_all_contacts():
            id, *contact = contact_data
            contacts_list.add_row(*contact, key=id)

    def action_target_dark(self):
        self.dark = not self.dark

    def action_request_quit(self):
        def check_answer(accepted):
            if accepted:
                self.exit()
        self.push_screen(QuestionDialog("Do you want to quit?"), check_answer)

    @on(Button.Pressed, "#add")
    def action_add(self):
        def check_contact(contact_data):
            if contact_data:
                self.db.add_contact(contact_data)
                id, *contact = self.db.get_last_contact()
                self.query_one(DataTable).add_row(*contact, key=id)
                self._refresh_contacts()

        self.push_screen(InputDialog(), check_contact)

    @on(Button.Pressed, "#edit")
    def action_edit(self):
        contacts_list = self.query_one(DataTable)
        row_key, _ = contacts_list.coordinate_to_cell_key(contacts_list.cursor_coordinate)

        if row_key is not None:
            existing_data = contacts_list.get_row(row_key)  # Get existing contact data

            def check_contact(updated_data):
                if updated_data:
                    self.db.update_contact(id=row_key.value, new_data=updated_data)
                    self._refresh_contacts()  # Call refresh method after update

            # Pass existing data to the InputDialog to pre-fill the fields
            self.push_screen(InputDialog(existing_data), check_contact)

    def _refresh_contacts(self):
        """Helper method to reload contacts from the database into the DataTable."""
        contacts_list = self.query_one(DataTable)
        contacts_list.clear()  # Clear all existing rows
        self._load_contacts()  # Reload contacts from the database


    @on(Button.Pressed, "#delete")
    def action_delete(self):
        contacts_list = self.query_one(DataTable)
        row_key, _ = contacts_list.coordinate_to_cell_key(contacts_list.cursor_coordinate)

        def check_answer(accepted):
            if accepted and row_key:
                self.db.delete_contact(id=row_key.value)
                contacts_list.remove_row(row_key)

        name = contacts_list.get_row(row_key)[0]
        self.push_screen(
            QuestionDialog(f"Do you want to delete {name}'s contact?"),
            check_answer,
        )
    
    def on_key(self, event) -> None:
        """Handle key presses for custom bindings."""
        if event.key == "j":
            self.query_one(DataTable).action_cursor_down()  # Move cursor down
        elif event.key == "k":
            self.query_one(DataTable).action_cursor_up()    # Move cursor up
    
class InputDialog(Screen):
    def __init__(self, existing_data=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.existing_data = existing_data or ("", "", "")  # Default to empty if None

    def compose(self):
        name, phone, email = self.existing_data
        yield Grid(
            Label("Edit Contact" if self.existing_data[0] else "Add Contact", id="title"),
            Label("Name:", classes="label"),
            Input(value=name, placeholder="Contact Name", classes="input", id="name"),  # Pre-fill with name
            Label("Phone:", classes="label"),
            Input(value=phone, placeholder="Contact Phone", classes="input", id="phone"),  # Pre-fill with phone
            Label("Email:", classes="label"),
            Input(value=email, placeholder="Contact Email", classes="input", id="email"),  # Pre-fill with email
            Static(),
            Button("OK", variant="success", id="ok"),
            Button("Cancel", variant="warning", id="cancel"),
            id="input-dialog",
        )
    def on_button_pressed(self, event):
        if event.button.id == "ok":
            name = self.query_one("#name", Input).value.rstrip()
            phone = self.query_one("#phone", Input).value
            email = self.query_one("#email", Input).value
            self.dismiss((name, phone, email))
        else:
            self.dismiss(())

class QuestionDialog(Screen):
    def __init__(self, message, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.message = message

    def compose(self):
        no_button = Button("No", variant="primary", id="no")
        no_button.focus()

        yield Grid(
            Label(self.message, id="question"),
            Button("Yes", variant="error", id="yes"),
            no_button,
            id="question-dialog"
        )

    def on_button_pressed(self, event):
        if event.button.id == "yes":
            self.dismiss(True)
        else:
            self.dismiss(False)



    




    