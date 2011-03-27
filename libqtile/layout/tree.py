
from base import Layout
from .. import manager
from .. import window
from .. import drawer
from .. import hook

class TreeNode(object):

    def __init__(self):
        self.children = []

    def add(self, node):
        node.parent = self
        self.children.append(node)

    def draw(self, layout, top, level=0):
        for i in self.children:
            top = i.draw(layout, top, level)
        return top

    def get_first_window(self):
        if isinstance(self, Window):
            return self
        for i in self.children:
            node = i.get_first_window()
            if node:
                return node

    def get_last_window(self):
        for i in reversed(self.children):
            node = i.get_last_window()
            if node:
                return node
        if isinstance(self, Window):
            return self

    def get_next_window(self):
        if self.children:
            return self.children[0]
        parent = self.parent
        node = self
        idx = 10000000
        while idx >= len(node.children)-1:
            idx = parent.children.index(node)
            node = parent
            if isinstance(node, Root):
                return None
            parent = node.parent
        return node.children[idx+1].get_first_window()

    def get_prev_window(self):
        parent = self.parent
        node = self
        idx = 0
        while idx <= 0:
            idx = parent.children.index(node)
            node = parent
            if idx == 0 and isinstance(node, Window):
                return node
            if isinstance(node, Root):
                return None
            parent = node.parent
        return node.children[idx-1].get_last_window()

class Root(TreeNode):

    def __init__(self, sections, default_section=None):
        super(Root, self).__init__()
        self.sections = {}
        for s in sections:
            node = Section(s)
            node.parent = self
            self.sections[s] = node
            self.children.append(node)
        if default_section is None:
            self.def_section = self.children[0]
        else:
            self.def_section = self.sections[default_section]

    def add(self, win):
        sect = getattr(win, 'tree_section', None)
        if sect is None:
            parent = self.sections.get(sect)
        if parent is None:
            parent = self.def_section
        node = Window(win)
        parent.add(node)
        return node

class Section(TreeNode):

    def __init__(self, title):
        super(Section, self).__init__()
        self.title = title

    def draw(self, layout, top, level=0):
        layout._layout.font_size = layout.section_fontsize
        layout._layout.text = self.title
        layout._layout.colour = layout.section_fg
        del layout._layout.width  # no centering
        layout._drawer.draw_hbar(layout.section_fg,
            0, layout.panel_width, top, linewidth=1)
        layout._layout.draw(layout.section_left, top + layout.section_top)
        top += (layout._layout.height +
            layout.section_top + layout.section_padding)
        top = super(Section, self).draw(layout, top, level)
        return top + layout.section_bottom

class Window(TreeNode):

    def __init__(self, win):
        super(Window, self).__init__()
        self.window = win

    def draw(self, layout, top, level=0):
        left = layout.padding_left + level*layout.level_shift
        layout._layout.font_size = layout.fontsize
        layout._layout.text = self.window.name
        if self.window is layout._focused:
            fg = layout.active_fg
            bg = layout.active_bg
        else:
            fg = layout.inactive_fg
            bg = layout.inactive_bg
        layout._layout.colour = fg
        layout._layout.width = layout.panel_width - left
        framed = layout._layout.framed(layout.border_width, bg,
            layout.padding_x, layout.padding_y)
        framed.draw_fill(left, top)
        top += framed.height + layout.vspace + layout.border_width
        return super(Window, self).draw(layout, top, level+1)

    def remove(self):
        if not self.children:
            self.parent.children.remove(self)
        elif len(self.children) == 1:
            self.parent.add(self.children[0])
        else:
            head = self.children[0]
            self.parent.add(head)
            for i in self.children[1:]:
                head.add(i)
        del self.children

class TreeTab(Layout):
    """Tree Tab Layout

    This layout works just like Max but displays tree of the windows at the
    left border of the screen, which allows you to overview all opened windows.
    It's designed to work with ``uzbl-browser`` but works with other windows
    too.
    """

    name = "treetab"
    defaults = manager.Defaults(
        ("bg_color", "000000", "Background color of tabs"),
        ("active_bg", "000080", "Background color of active tab"),
        ("active_fg", "ffffff", "Foreground color of active tab"),
        ("inactive_bg", "606060", "Background color of inactive tab"),
        ("inactive_fg", "ffffff", "Foreground color of inactive tab"),
        ("margin_left", 6, "Left margin of tab panel"),
        ("margin_y", 6, "Vertical margin of tab panel"),
        ("padding_left", 6, "Left padding for tabs"),
        ("padding_x", 6, "Left padding for tab label"),
        ("padding_y", 2, "Top padding for tab label"),
        ("border_width", 2, "Width of the border"),
        ("vspace", 2, "Space between tabs"),
        ("level_shift", 8, "Shift for children tabs"),
        ("font", "Arial", "Font"),
        ("fontsize", 14, "Font pixel size."),
        ("section_fontsize", 11, "Font pixel size of section label"),
        ("section_fg", "ffffff", "Color of section label"),
        ("section_top", 4, "Top margin of section label"),
        ("section_bottom", 6, "Bottom margin of section"),
        ("section_padding", 4, "Bottom of magin section label"),
        ("section_left", 4, "Left margin of section label"),
        ("panel_width", 150, "Width of the left panel"),
        ("sections", ['Surfing', 'News', 'Incognito'],
            "Foreground color of inactive tab"),
    )

    def __init__(self, **config):
        Layout.__init__(self, **config)
        self._focused = None
        self._panel = None
        self._tree = Root(self.sections)
        self._nodes = {}

    def clone(self, group):
        c = Layout.clone(self, group)
        c._focused = None
        c._panel = None
        c._tree = Root(self.sections)
        return c

    def focus_first(self):
        res = self._tree.get_first_window()
        if res:
            return res.window

    def focus_last(self):
        res = self._tree.get_last_window()
        if res:
            return res.window

    def focus_next(self, win):
        res = self._nodes[win].get_next_window()
        if res:
            return res.window

    def focus_prev(self, win):
        res = self._nodes[win].get_prev_window()
        if res:
            return res.window

    def focus(self, win):
        self._focused = win

    def blur(self):
        self._focused = None

    def add(self, win):
        self._nodes[win] = self._tree.add(win)

    def remove(self, win):
        res = self.focus_next(win)
        if self._focused is win:
            self._focused = None
        self._nodes[win].remove()
        del self._nodes[win]
        return res

    def _create_panel(self):
        self._panel = window.Internal.create(self.group.qtile,
            self.group.screen.dx,
            self.group.screen.dy,
            self.panel_width,
            self.group.screen.dheight)
        self._create_drawer()
        self._panel.handle_Expose = self._panel_Expose
        self._panel.handle_ButtonPress = self._panel_ButtonPress
        hook.subscribe.window_name_change(self.draw_panel)
        hook.subscribe.focus_change(self.draw_panel)

    def _panel_Expose(self):
        self.draw_panel()

    def draw_panel(self):
        if not self._panel:
            return
        self._drawer.clear(self.bg_color)
        self._tree.draw(self, 0)
        self._drawer.draw(0, self.panel_width)

    def _panel_ButtonPress(self):
        pass  # TODO

    def configure(self, c):
        if not self._panel:
            self._create_panel()
            self._panel.unhide()
            self.draw_panel()
        if self._nodes and c is self._focused:
            c.place(
                self.group.screen.dx + self.panel_width,
                self.group.screen.dy,
                self.group.screen.dwidth - self.panel_width,
                self.group.screen.dheight,
                0,
                None
            )
            c.unhide()
        else:
            c.hide()

    def info(self):
        d = Layout.info(self)
        d["clients"] = [i.name for i in self._nodes]
        return d

    def cmd_down(self):
        """
            Switch down in the window list
        """
        win = self.focus_next(self._focused)
        if not win:
            win = self.focus_first()
        self.group.focus(win, False)

    def cmd_up(self):
        """
            Switch up in the window list
        """
        win = self.focus_prev(self._focused)
        if not win:
            win = self.focus_last()
        self.group.focus(win, False)

    def cmd_move_up(self):
        win = self._focused
        if not win:
            return
        node = self._nodes[win]
        p = node.parent.children
        idx = p.index(node)
        if idx > 0:
            p[idx] = p[idx-1]
            p[idx-1] = node
        self.draw_panel()

    def cmd_move_down(self):
        win = self._focused
        if not win:
            return
        node = self._nodes[win]
        p = node.parent.children
        idx = p.index(node)
        if idx < len(p)-1:
            p[idx] = p[idx+1]
            p[idx+1] = node
        self.draw_panel()

    def cmd_move_left(self):
        win = self._focused
        if not win:
            return
        node = self._nodes[win]
        if not isinstance(node.parent, Section):
            node.parent.children.remove(node)
            node.parent.parent.add(node)
        self.draw_panel()

    def cmd_move_right(self):
        win = self._focused
        if not win:
            return
        node = self._nodes[win]
        idx = node.parent.children.index(node)
        if idx > 0:
            node.parent.children.remove(node)
            node.parent.children[idx-1].add(node)
        self.draw_panel()

    def cmd_increase_ratio(self):
        self.panel_width += 10
        self._resize_panel()
        self.group.layoutAll()

    def cmd_decrease_ratio(self):
        self.panel_width -= 10
        self._resize_panel()
        self.group.layoutAll()

    def _create_drawer(self):
        self._drawer = drawer.Drawer(self.group.qtile, self._panel.window.wid,
            self.panel_width, self.group.screen.dheight)
        self._drawer.clear(self.bg_color)
        self._layout = self._drawer.textlayout("", "ffffff", self.font,
            self.fontsize, wrap=False)

    def _resize_panel(self):
        if self._panel:
            self._panel.place(
                self.group.screen.dx,
                self.group.screen.dy,
                self.panel_width,
                self.group.screen.dheight,
                0,
                None
            )
            self._create_drawer()
            self.draw_panel()
