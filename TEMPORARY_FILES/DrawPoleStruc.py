# NEW Structure for the pole structure
# Not ready yet with the yaml parameters methods

import pyvista as pv
from abc import ABC, abstractmethod

class PVStructure(ABC):
    def __init__(self):
        pass

class PVModeler(PVStructure):
    ''' 
    This class is responsible for modeling vertical and horizontal bars.
    '''
    def __init__(self, mesh, **kwargs):
        super().__init__(mesh, **kwargs)
      
    @staticmethod
    def Pole(form: str, x_length: float, y_length: float, z_length: float) -> pv.PolyData:
        '''
        Draw a vertical bar
        
        Args:
            form (str) : choose if you want a cube base bar or cylender one
            x_length (int) : specify the thickness of the x-axis or the base cylinder radius
            y_length (int) : specify the thickness of the y-axis
            z_length (int) : specify the Height of the bar
        '''

        if form == 'cube':
            bar = pv.Cube(
                x_length=x_length,
                y_length=y_length,
                z_length=z_length,
                center=(0.0, 0.0, 0.0),
            )
            bar.triangulate(inplace=True)
            return bar
        
        elif form == 'cylinder':
              bar = pv.Cylinder(
                  height=z_length,
                  radius=x_length,
                  center=(0.0, 0.0, 0.0),
                  direction=(0.0, 0.0, 1.0), # cylinder base face to z-axis
              )
              bar.triangulate(inplace=True)
              return bar
        
    @staticmethod    
    def Purlin(form: str, x_length: float, y_length: float, z_length: float) -> pv.PolyData:
        '''
        Draw an horizontal bar
        
        Args:
            form (str) : choose if you want a cube base bar or cylender one
            x_length (int) : specify the thickness of the x-axis or the base cylinder radius
            y_length (int) : specify the thickness of the y-axis
            z_length (int) : specify the length of the bar '''
        
        if form == 'cube':
            bar = pv.Cube(
                x_length=x_length,
                y_length=y_length,
                z_length=z_length,
                center=(0.0, 0.0, 0.0),
            )
            bar.triangulate(inplace=True)
            return bar
        
        elif form == 'cylinder':
              bar = pv.Cylinder(
                  height=z_length,
                  radius=x_length,
                  center=(0.0, 0.0, 0.0),
                  direction=(1.0, 0.0, 0.0), # cylinder base face to x-axis
              )
              bar.triangulate(inplace=True)
              return bar

    @staticmethod
    def Panel(x_length: float, y_length: float, z_length: float) -> pv.PolyData:
        panel = pv.Cube(
              x_length=x_length, 
              y_length=y_length, 
              z_length=z_length, 
              center=(0.0, 0.0, 0.0)
              )
        panel.triangulate(inplace=True)
        return panel

class AgrivoltaicFence(PVStructure):
    def __init__(self, mesh, **kwargs):
        super().__init__(mesh, **kwargs)

    @staticmethod
    def makeFence() -> pv.PolyData:
        '''
        creates a structure by combining vertical and horizontal bars 
        '''
        xlen = 0.2
        ylen = 0.2
        zlen = 5.0

        pole = PVModeler.Pole("cube", xlen,  ylen,  zlen)
        
        purlin_1 = PVModeler.Purlin("cylinder", xlen / 2, ylen / 2, zlen)
        purlin_1.translate((zlen / 2, 0.0, zlen / 2), 
                             inplace=True)
        
        purlin2 = PVModeler.Purlin("cylinder", xlen / 2, ylen / 2, zlen)
        purlin2.translate((zlen / 2, 0.0, 0.0),
                             inplace=True)
        
        return pole + purlin_1 + purlin2

    @staticmethod
    def multiFence(
        x_groups: int,
        y_groups: int,
        x_spacing: float,
        y_spacing: float,
        xlen: float = 0.2,
        ylen: float = 0.2,
        zlen: float = 5.0,
    ) -> pv.MultiBlock:
        '''
        Build a grid of bar groups arranged along the X and Y axes.

        Args:
            x_groups (int): Number of groups to create along the X axis.
            y_groups (int): Number of groups to create along the Y axis.
            x_spacing (float): Distance between consecutive groups along the X axis.
            y_spacing (float): Distance between consecutive groups along the Y axis.
            xlen (float, optional): Length of the bars along X. Default is 0.2.
            ylen (float, optional): Length of the bars along Y. Default is 0.2.
            zlen (float, optional): Height of the bars along Z. Default is 5.0.

        Returns:
            pv.MultiBlock: A MultiBlock container with all bar groups and terminal bars.
        '''
        blocks = pv.MultiBlock()

        for j in range(y_groups):
            for i in range(x_groups):
                g = AgrivoltaicFence.makeFence()
                g.translate((i * x_spacing, j * y_spacing, 0.0), inplace=True)
                blocks.append(g)

            end_pole = PVModeler.Pole("cube", xlen, ylen, zlen)
            end_pole.translate((x_groups * x_spacing, j * y_spacing, 0.0), inplace=True)
            blocks.append(end_pole)

        return blocks

if __name__ == "__main__":
    mesh = AgrivoltaicFence.multiFence(5, 3, 5.0, 5.0, 0.2, 0.2, 5.0) 
    mesh.plot(show_edges=True)