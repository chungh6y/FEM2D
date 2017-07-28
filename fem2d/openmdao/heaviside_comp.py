import numpy as np

from openmdao.api import ExplicitComponent


class HeavisideComp(ExplicitComponent):

    def initialize(self):
        self.metadata.declare('num', type_=int, required=True)

    def setup(self):
        num = self.metadata['num']

        self.add_input('x', shape=num)
        self.add_output('y', shape=num)

        arange = np.arange(num)
        self.declare_partials('y', 'x', rows=arange, cols=arange)

    def compute(self, inputs, outputs):
        outputs['y'] = 0.5 + 0.5 * np.tanh(inputs['x']) + 0.01

    def compute_partials(self, inputs, outputs, partials):
        partials['y', 'x'] = 0.5 / np.cosh(inputs['x']) ** 2
