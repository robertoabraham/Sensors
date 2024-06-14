#!/home/dragonfly/miniforge3/envs/active_optics/bin/python

from dragonfly.find import find_mount_info_in_log
from dragonfly.find import find_powerbox_info_in_log
from dragonfly.find import find_camera_info_in_log
from dragonfly.find import find_lens_info_in_log

from rich.text import Text

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, Tree
from textual.widgets.tree import TreeNode

import sys


class DragonflyElementTree(Static):
    """A widget to display a Dragonfly element as a tree."""

    tree = Tree("Dragonfly001")
    mount_data = {}
    powerbox_data = {}
    aluma_data = {}
    starchaser_data = {}
    lens_data = {}
    mount_node = tree.root.add("Mount")
    powerbox_node = tree.root.add("Powerbox")
    lens_node = tree.root.add("Canon")
    aluma_node = tree.root.add("Aluma")
    starchaser_node = tree.root.add("Starchaser")

    def on_mount(self) -> None:
        """Event handler called when widget is added to the app."""
        self.update_data()
        self.tree.root.expand()
        self.update_timer = self.set_interval(3, self.update_data)

    def update_data(self) -> None:
        """Update the data displayed in the widget."""
        try:
            self.mount_data = find_mount_info_in_log()
        except:
            self.mount_data = {}
        try:    
            self.powerbox_data = find_powerbox_info_in_log()
        except:
            self.powerbox_data = {}
        try:
            self.aluma_data = find_camera_info_in_log("aluma")
        except:
            self.aluma_data = {}
        try:
            self.starchaser_data = find_camera_info_in_log("starchaser")
        except:
            self.starchaser_data = {}
        try:
            self.lens_data = find_lens_info_in_log()
        except:
            self.lens_data = {}
        self.add_data(self.mount_node, "Astro-Physics Mount", self.mount_data)
        self.add_data(self.powerbox_node, "Pegasus Powerbox", self.powerbox_data)
        self.add_data(self.lens_node, "Canon Lens", self.lens_data)
        self.add_data(self.aluma_node, "Aluma Camera", self.aluma_data)
        self.add_data(self.starchaser_node, "Starchaser Camera", self.starchaser_data)

    def compose(self) -> ComposeResult:
        """Compose the widget."""
        yield self.tree

    @classmethod
    def add_data(cls, node: TreeNode, data_name: str, add_data: object) -> None:
        """Adds data to a tree node.

        Args:
            node (TreeNode): A Tree node.
            data_name (str): Name of the object
            data (object): Any python object.
        """

        from rich.highlighter import ReprHighlighter

        highlighter = ReprHighlighter()

        def add_node(name: str, node: TreeNode, data: object, augment: bool = False) -> None:
            """Adds a node to the tree.

            Args:
                name (str): Name of the node.
                node (TreeNode): Parent node.
                data (object): Data associated with the node.
            """
            if not augment:
                node.remove_children()
            if isinstance(data, dict):
                node.set_label(Text(f"{{}} {name}"))
                for key, value in data.items():
                    new_node = node.add("")
                    add_node(key, new_node, value)
            elif isinstance(data, list):
                node.set_label(Text(f"[] {name}"))
                for index, value in enumerate(data):
                    new_node = node.add("")
                    add_node(str(index), new_node, value)
            else:
                node.allow_expand = False
                if name:
                    label = Text.assemble(
                        Text.from_markup(f"[b]{name}[/b]="), highlighter(repr(data))
                    )
                else:
                    label = Text(repr(data))
                node.set_label(label)
        add_node(data_name, node, add_data)

class DragonflyLogMonitor(App):

    BINDINGS = [
        ("t", "toggle_root", "Toggle root"),
        ("q", "quit", "Exit application"),
    ]
    
    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield DragonflyElementTree()
        
    def action_quit(self) -> None:
        """Exit application."""
        sys.exit()

    def action_toggle_root(self) -> None:
        """Toggle the root node."""
        tree = self.query_one(DragonflyElementTree).tree
        tree.show_root = not tree.show_root


if __name__ == "__main__":
    app = DragonflyLogMonitor()
    app.run()
