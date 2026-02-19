from typing import *
from copy import *

class BoolLiteral:
	"""
	A boolean literal for `variable`. If `polarity` == True then the literal is
	positive, and if `poliary` == False then the literal is negative.
	"""
	def __init__(self, variable: str, polarity: bool):
		self.variable = variable
		self.polarity = polarity

	def __repr__(self) -> str:
		prefix = ""
		if not self.polarity:
			prefix = "¬"
		return prefix + self.variable

	def __eq__(self, other: BoolLiteral) -> bool:
		return self.variable == other.variable and self.polarity == other.polarity

	def is_pos(self, variable: str) -> bool:
		return self.variable == variable and self.polarity == True

	def is_neg(self, variable: str) -> bool:
		return self.variable == variable and self.polarity == False

	def make_pos(variable: str) -> BoolLiteral:
		return BoolLiteral(variable, True)

	def make_neg(variable: str) -> BoolLiteral:
		return BoolLiteral(variable, False)

	def negate(self) -> BoolLiteral:
		return BoolLiteral(self.variable, not self.polarity)

	def __hash__(self):
		return hash((self.variable, self.polarity))

class Clause:
	"""
	A CNF clause.
	"""
	def __init__(self, *literals: BoolLiteral):
		self.literals = set(literals)

	def __repr__(self) -> str:
		return self.literals.__repr__()

	def make(*lit_strings: str) -> Clause:
		literals = []
		for lit_string in lit_strings:
			if lit_string[0] == '-':
				literals.append(BoolLiteral.make_neg(lit_string[1:]))
			else:
				literals.append(BoolLiteral.make_pos(lit_string))
		return Clause(*literals)

	def __iter__(self):
		return iter(self.literals)

class ImplicationGraph:
	"""
	An implication graph.
	"""
	def __init__(self, edges: dict[BoolLiteral, set(BoolLiteral)]={}, conflict_clause: set(BoolLiteral)=None):
		self.edges = edges
		self.conflict_clause = conflict_clause

	def add_node(self, node: BoolLiteral):
		self.edges[node] = set()

	def add_edge(self, src: BoolLiteral, tgt: BoolLiteral):
		self.edges[tgt].add(src)

	def add_conflict(self, srcs: set(BoolLiteral)):
		self.conflict_clause = srcs

	def explain(self, node: BoolLiteral):
		self.conflict_clause.discard(node.negate())
		for parent in self.edges[node]:
			self.conflict_clause.add(parent.negate())

	def __repr__(self) -> str:
		string = ""
		for tgt in self.edges:
			for src in self.edges[tgt]:
				string += repr(src) + ' -> ' + repr(tgt) + '\n'
		return string

	def __deepcopy__(self) -> ImplicationGraph:
		return ImplicationGraph(deepcopy(self.edges), copy(self.conflict_clause))

class Model:
	"""
	A variable assignment.
	"""
	def __init__(self):
		self.assignment = []
		self.decision_level = 0
		self.decisions = []
		self.decision_levels = {}

	def assign(self, literal: BoolLiteral):
		self.assignment.append(literal)
		self.decision_levels[literal] = self.decision_level

	def decide(self, literal: BoolLiteral):
		self.decisions.append(len(self.assignment))
		self.assignment.append(literal)
		self.decision_level += 1
		self.decision_levels[literal] = self.decision_level

	def backjump(self, decision_level: int):
		idx = self.decisions[decision_level]
		self.assignment = self.assignment[:idx]
		self.decisions = self.decisions[:decision_level]
		self.decision_level = decision_level
		# TODO -- do we want to delete the removed literals from decision level dict here?

	def get_current_decision_literals(self) -> list[BoolLiteral]:
		return self.assignment[self.decisions[-1]:]

	def get_last_literal(self) -> BoolLiteral:
		return self.assignment[-1]

	def contains(self, literal: BoolLiteral) -> bool:
		return literal in self.assignment

	def get_level(self, literal: BoolLiteral) -> int:
		level = self.decision_levels.get(literal)
		if level is not None:
			return level
		return -1

	def __repr__(self) -> str:
		model_string = ''
		if self.decision_level == 0:
			for literal in self.assignment:
				model_string += repr(literal) + ' '
			return model_string
		last_level = 0
		for level in self.decisions:
			for literal in self.assignment[last_level:level]:
				model_string += repr(literal) + ' '
			model_string += '• '
			last_level = level
		for literal in self.assignment[self.decisions[-1]:]:
				model_string += repr(literal) + ' '
		return model_string

	def __iter__(self):
		return iter(self.assignment)

class State:
	"""
	State for the CDCL proof system, consisting of
	- A collection of clauses
	- A partial assignment to literals
	- A conflict clause (None if no conflict)
	"""
	def __init__(self, clauses: List[Clause]):
		self.clauses = clauses
		self.model = Model()
		self.conflict = None
		self.unsat = False
		self.sat = False

	def __repr__(self) -> str:
		if self.unsat:
			return "UNSAT"
		if self.sat:
			return "SAT"
		state_string = 'Δ = ' + repr(self.clauses) + '\n'
		state_string += 'M = ' + repr(self.model) + '\n'
		state_string += 'C = '
		if self.conflict is not None:
			state_string += repr(self.conflict) + '\n'
		else:
			state_string += 'no\n'
		return state_string

class Core:
	""" 
	Maintains state for CDCL core. Query to access conflict graph, unassigned 
	literals, conflict state, etc.
	"""
	def __init__(self, state: State):
		self.graphs = [ImplicationGraph()]
		self.graph = self.graphs[-1]
		self.in_conflict = False
		self.state = state

	def propagate(self, clause_idx: int) -> bool:
		clause = self.state.clauses[clause_idx]
		unassigned_lit = None
		num_unassigned = 0

		for literal in clause:
			if literal.negate() not in self.state.model:
				num_unassigned += 1
				unassigned_lit = literal

		if num_unassigned == 1 and unassigned_lit not in self.state.model and unassigned_lit.negate() not in self.state.model:
			self.state.model.assign(unassigned_lit)
			self.graph.add_node(unassigned_lit)
			for literal in clause.literals - {unassigned_lit}:
				self.graph.add_edge(literal.negate(), unassigned_lit)

			return True
		return False

	def decide(self, literal: BoolLiteral) -> bool:
		if literal not in self.state.model and literal.negate() not in self.state.model:
			self.state.model.decide(literal)
			self.graphs.append(self.graph.__deepcopy__())
			self.graph = self.graphs[-1]
			return True
		return False

	def conflict(self, clause_idx: int) -> bool:
		if not self.in_conflict:
			clause = self.state.clauses[clause_idx]
			for literal in clause:
				if literal.negate() not in self.state.model:
					return False
			self.in_conflict = True
			self.graph.add_conflict(clause.literals)
			self.state.conflict = self.graph.conflict_clause
			return True
		return False

	def explain(self) -> bool:
		decision_literals = self.state.model.get_current_decision_literals()
		while len(decision_literals) > 1:
			last_literal = self.state.model.assignment.pop(-1)
			self.graph.explain(last_literal)
			decision_literals = decision_literals[:-1]
		return True

	def backjump(self, decision_level: int) -> bool:
		if self.in_conflict:
			conflict_clause = self.graph.conflict_clause
			decision_literal = self.state.model.get_last_literal()
			level = -1
			for literal in conflict_clause - {decision_literal}:
				level = max(level, self.state.model.get_level(literal))
			if decision_level >= level:
				self.in_conflict = False
				self.state.model.backjump(decision_level)
				self.state.model.assign(decision_literal.negate())
				self.state.conflict = None
				self.graphs = self.graphs[:decision_level + 1]
				self.graph = self.graphs[-1]
				return True
		return False

	def fail(self) -> bool:
		if self.state.model.decision_level == 0 and self.in_conflict:
			self.state.unsat = True
			return True
		return False

	def __repr__(self) -> str:
		core_string = 'State:\n' + repr(self.state)
		core_string += 'Implication Graph:\n' + repr(self.graph)
		return core_string