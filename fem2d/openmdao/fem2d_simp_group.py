import numpy as np

from openmdao.api import Group, IndepVarComp

from fem2d.openmdao.penalization_comp import PenalizationComp
from fem2d.openmdao.heaviside_comp import HeavisideComp
from fem2d.openmdao.states_comp import StatesComp
from fem2d.openmdao.disp_comp import DispComp
from fem2d.openmdao.compliance_comp import ComplianceComp
from fem2d.openmdao.weight_comp import WeightComp
from fem2d.openmdao.objective_comp import ObjectiveComp
from fem2d.fem2d import PyFEMSolver
from fem2d.utils.rbf import get_rbf_mtx
from fem2d.utils.bspline import get_bspline_mtx


class FEM2DSimpGroup(Group):

    def initialize(self):
        self.metadata.declare('fem_solver', type_=PyFEMSolver, required=True)
        self.metadata.declare('num_nodes_x', type_=int, required=True)
        self.metadata.declare('num_nodes_y', type_=int, required=True)
        self.metadata.declare('forces', type_=np.ndarray, required=True)
        self.metadata.declare('p', type_=(int, float), required=True)
        self.metadata.declare('w', type_=(int, float), required=True)
        self.metadata.declare('nodes', type_=np.ndarray, required=True)
        self.metadata.declare('volume_fraction', type_=(int, float), required=True)

    def setup(self):
        fem_solver = self.metadata['fem_solver']
        num_nodes_x = self.metadata['num_nodes_x']
        num_nodes_y = self.metadata['num_nodes_y']
        forces = self.metadata['forces']
        p = self.metadata['p']
        w = self.metadata['w']
        nodes = self.metadata['nodes']
        volume_fraction = self.metadata['volume_fraction']

        num = num_nodes_x * num_nodes_y

        state_size = 2 * num_nodes_x * num_nodes_y + 2 * num_nodes_y
        disp_size = 2 * num_nodes_x * num_nodes_y

        rhs = np.zeros(state_size)
        rhs[:disp_size] = forces

        # inputs
        comp = IndepVarComp()
        comp.add_output('rhs', val=rhs)
        comp.add_output('forces', val=forces)

        comp.add_output('dvs', val=0.5, shape=num)
        comp.add_design_var('dvs', lower=0.01, upper=1.0)
        # comp.add_design_var('x', lower=-4, upper=4)
        self.add_subsystem('inputs_comp', comp)
        self.connect('inputs_comp.dvs', 'penalization_comp.x')
        self.connect('inputs_comp.dvs', 'weight_comp.x')

        # penalization
        comp = PenalizationComp(num=num, p=p)
        self.add_subsystem('penalization_comp', comp)

        self.connect('penalization_comp.y', 'states_comp.multipliers')

        # states
        comp = StatesComp(fem_solver=fem_solver, num_nodes_x=num_nodes_x, num_nodes_y=num_nodes_y,
            nodes=nodes)
        self.add_subsystem('states_comp', comp)
        self.connect('inputs_comp.rhs', 'states_comp.rhs')

        # disp
        comp = DispComp(num_nodes_x=num_nodes_x, num_nodes_y=num_nodes_y)
        self.add_subsystem('disp_comp', comp)
        self.connect('states_comp.states', 'disp_comp.states')

        # compliance
        comp = ComplianceComp(num_nodes_x=num_nodes_x, num_nodes_y=num_nodes_y)
        self.add_subsystem('compliance_comp', comp)
        self.connect('disp_comp.disp', 'compliance_comp.disp')
        self.connect('inputs_comp.forces', 'compliance_comp.forces')

        # weight
        comp = WeightComp(num=num)
        comp.add_constraint('weight', upper=volume_fraction)
        self.add_subsystem('weight_comp', comp)

        # objective
        comp = ObjectiveComp(w=w)
        comp.add_objective('objective')
        self.add_subsystem('objective_comp', comp)
        self.connect('compliance_comp.compliance', 'objective_comp.compliance')
        self.connect('weight_comp.weight', 'objective_comp.weight')
