import cartopy.crs as ccrs
import matplotlib.pyplot as plt
import matplotlib.colors as c
import iris
import iris.plot as iplt
import numpy as np	
from matplotlib.figure import Figure
from matplotlib.backends.backend_gtkagg import FigureCanvasGTKAgg as FigureCanvas
from matplotlib.backends.backend_gtkagg import NavigationToolbar2GTKAgg
import gtk

class NavigationToolbar(NavigationToolbar2GTKAgg):
    
    def __init__(self, canvas, window):
        
        self.undo_flag = False
        
        self.canvas = canvas

        self.toolitems = (('Home', 'Reset original view', 'home', 'home'),
            ('Back', 'Back to  previous view', 'back', 'back'),
            ('Forward', 'Forward to next view', 'forward', 'forward'),
            (None, None, None, None),
            ('Pan', 'Pan axes with left mouse, zoom with right', 'move', 'pan'),
            ('Zoom', 'Zoom to rectangle', 'zoom_to_rect', 'zoom'),
            (None, None, None, None),
            ('Subplots', 'Configure subplots', 'subplots', 'configure_subplots'),
            ('Save', 'Save the figure', 'filesave', 'save_figure'),
            (None, None, None, None),
            (None, None, None, None),
            ("Undo", "Undo last data action", "back", "undo"),
            ("Edit", "Edit data", "hand", "set_drawing"),
            )
        super(NavigationToolbar, self).__init__(canvas, window)
    
    def undo(self, *args):
        self.undo_flag = True
        self.canvas.draw()
    
    def set_drawing(self, *args):
        if self._active == "PAN":
            self.pan(*args)
        self._active = "DRAWING"
        self.mode = "Edit"

class Editor():

    def __init__(self):

        self.diffs = []
        self.current_diff = []

        self.mask = [(i,j) for i in range(-4,5) for j in range(-4,5)]
        

        self.win = gtk.Window()
        self.win.connect("destroy", lambda x: gtk.main_quit())
        self.win.set_default_size(700,700)
        self.win.set_title("Data mask app thing")

        vbox = gtk.VBox()
        self.win.add(vbox)

        cube = iris.load_cube(iris.sample_data_path("uk_hires.pp"), "air_potential_temperature")

        rand_data = np.random.randint(2, size=cube.shape)

        cube.data = rand_data

        self.cMap = c.ListedColormap(["b", "w"])


        x_coord = cube.coord(axis="X")
        y_coord = cube.coord(axis="Y")

        self.x = x_coord.points

        self.y = y_coord.points

        x_dim, = cube.coord_dims(x_coord)
        y_dim, = cube.coord_dims(y_coord)

        key = list(cube.shape)

        for i in range(len(key)):
            
            if i == x_dim or i == y_dim:
                key[i] = tuple(range(key[i]))
            else:
                key[i] = 0

        self.cube = cube[tuple(key)]

        self.data_mesh = iplt.pcolormesh(self.cube, cmap=self.cMap)
        self.tmp_data = self.cube.data.copy()

        ax = plt.gca()
        ax.coastlines("50m", linewidth=2)

        self.canvas = FigureCanvas(plt.gcf())  # a gtk.DrawingArea
        
        self.canvas.mpl_connect('button_press_event', self)
        self.canvas.mpl_connect('motion_notify_event', self)
        self.canvas.mpl_connect('button_release_event', self)
        self.canvas.mpl_connect('draw_event', self)
        vbox.pack_start(self.canvas)
        self.toolbar = NavigationToolbar(self.canvas, self.win)
        vbox.pack_start(self.toolbar, False, False)

    def __call__(self, event):

        if self.toolbar._active == "DRAWING":
            if event.name == 'button_press_event':
                self.onclick(event)

            if event.name == 'motion_notify_event':
                self.ondrag(event)

        if event.name == 'button_release_event':
            self.onrelease(event)
        
        if event.name == 'draw_event':
            if self.toolbar.undo_flag:
                self._undo_last_diff()
                self.canvas.draw()

    def _locate_point_in_data(self, pt):
        
        if pt is None:
            return
     
        #pt = coord_sys.transform_point(pt[0], pt[1], platcar)
        x_ind = np.searchsorted(self.x, pt[0]+360)
        y_ind = np.searchsorted(self.y, pt[1])
        
        return (x_ind, y_ind)

    def onclick(self, event):

        
        pt = (event.xdata, event.ydata)

        x_ind, y_ind = self._locate_point_in_data(pt)
        
        self.cube.data[y_ind, x_ind] = (self.cube.data[y_ind, x_ind] + 1)%2
        
        self.data_mesh.set_array(self.cube.data.ravel())

        self.canvas.draw()

    def ondrag(self, event):
        if event.button is not None:
            pt = (event.xdata, event.ydata)

            x_ind, y_ind = self._locate_point_in_data(pt)
            

            for index in self.mask:

                self.current_diff.append((y_ind+index[0], x_ind+index[1], self.cube.data[y_ind+index[0], x_ind+index[1]]))
                self.tmp_data[y_ind+index[0], x_ind+index[1]] = event.button % 2

            self.data_mesh.set_array(self.tmp_data.ravel())
            self.canvas.draw()
             
    def _undo_last_diff(self):
        
        if len(self.diffs) > 0:
            diff = self.diffs[-1]

            for change in diff:

                self.cube.data[change[0], change[1]] = change[2]
            
            self.data_mesh.set_array(self.cube.data.ravel())

            del self.diffs[-1]
        
        self.tmp_data = self.cube.data.copy()
        self.toolbar.undo_flag = False

    def _apply_diff(self, diff, button):

        for change in diff:
            self.cube.data[change[0], change[1]] = button%2
        self.data_mesh.set_array(self.cube.data.ravel())
        self.canvas.draw()

    def onrelease(self, event):
        
        if len(self.current_diff)>0:
            self.diffs.append(self.current_diff)
            self._apply_diff(self.current_diff, event.button)
            self.current_diff = []
            self.tmp_data = self.cube.data.copy()

    def start(self):

        self.win.show_all()
        gtk.main()


if __name__ == "__main__":
    editor = Editor()
    editor.start()

