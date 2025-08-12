class ModsModel:
    def __init__(self, data: list[dict], on_change=None):
        self.data = data
        self.on_change = on_change  # callback to trigger UI update

    def swap(self, i, direction):
        new_index = i + direction
        if 0 <= new_index < len(self.data):
            self.data[i], self.data[new_index] = self.data[new_index], self.data[i]
            if self.on_change:
                self.on_change()

    def move(self, start_index, drop_index):
        # Move the item in the data list
        dragged_item = self.data.pop(start_index)
        # Adjust drop index if item was moved from above
        if start_index < drop_index:
            drop_index -= 1
        self.data.insert(drop_index, dragged_item)
        if self.on_change:
            self.on_change()

    def toggle_enable(self, index):
        self.data[index]["enabled"] = not self.data[index]["enabled"]

    def toggle_rewrite(self, index):
        self.data[index]["rewrite"] = not self.data[index]["rewrite"]
