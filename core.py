from typing import *
from copy import *

class BoolLiteral:
	"""
	A boolean literal for `variable`. If `polarity` == True then the literal is
	positive, and if `polarity` == False then the literal is negative.
	"""
	def __init__(self, variable: str, polarity: bool):
		self.variable = variable
		self.polarity = polarity

	def __repr__(self) -> str:
		prefix = ""
		if not self.polarity:
			prefix = "¬"
		return prefix + self.variable

	def __eq__(self, other) -> bool:
		if not isinstance(other, BoolLiteral):
			return False
		return self.variable == other.variable and self.polarity == other.polarity

	def __hash__(self):
		return hash((self.variable, self.polarity))

	def is_pos(self, variable: str) -> bool:
		return self.variable == variable and self.polarity is True

	def is_neg(self, variable: str) -> bool:
		return self.variable == variable and self.polarity is False

	@staticmethod
	def make_pos(variable: str):
		return BoolLiteral(variable, True)

	@staticmethod
	def make_neg(variable: str):
		return BoolLiteral(variable, False)

	def negate(self):
		return BoolLiteral(self.variable, not self.polarity)


class Clause:
	"""
	A CNF clause.
	"""
	def __init__(self, *literals: BoolLiteral):
		self.literals = set(literals)

	def __repr__(self) -> str:
		return self.literals.__repr__()

	@staticmethod
	def make(*lit_strings: str):
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
	def __init__(self, edges=None, conflict_clause=None):
		self.edges: Dict[BoolLiteral, Set[BoolLiteral]] = edges if edges is not None else {}
		self.conflict_clause: Optional[Set[BoolLiteral]] = conflict_clause

	def add_node(self, node: BoolLiteral):
		if node not in self.edges:
			self.edges[node] = set()

	def add_edge(self, src: BoolLiteral, tgt: BoolLiteral):
		if tgt not in self.edges:
			self.edges[tgt] = set()
		self.edges[tgt].add(src)

	def add_conflict(self, srcs: set[BoolLiteral]):
		self.conflict_clause = set(srcs)

	def explain(self, node: BoolLiteral):
		if self.conflict_clause is None:
			return
		self.conflict_clause.discard(node.negate())
		for parent in self.edges.get(node, []):
			self.conflict_clause.add(parent.negate())

	def __repr__(self) -> str:
		string = ""
		for tgt in self.edges:
			for src in self.edges[tgt]:
				string += repr(src) + ' -> ' + repr(tgt) + '\n'
		return string

	def __deepcopy__(self, memo):
		return ImplicationGraph(deepcopy(self.edges), deepcopy(self.conflict_clause))


class Model:
	"""
	A variable assignment.
	"""
	def __init__(self):
		self.assignment: List[BoolLiteral] = []
		self.decision_level = 0
		self.decisions: List[int] = []
		self.decision_levels: Dict[BoolLiteral, int] = {}

	def __contains__(self, literal: BoolLiteral) -> bool:
		return literal in self.assignment

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
		removed = self.assignment[idx:]
		self.assignment = self.assignment[:idx]
		self.decisions = self.decisions[:decision_level]
		self.decision_level = decision_level

		# Remove stale decision level mappings
		for lit in removed:
			if lit in self.decision_levels:
				del self.decision_levels[lit]

	def get_current_decision_literals(self) -> List[BoolLiteral]:
		if not self.decisions:
			return self.assignment
		return self.assignment[self.decisions[-1]:]

	def get_last_literal(self) -> BoolLiteral:
		return self.assignment[-1]

	def get_level(self, literal: BoolLiteral) -> int:
		return self.decision_levels.get(literal, -1)

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
	State for the CDCL proof system.
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
		state_string += repr(self.conflict) + '\n' if self.conflict else 'no\n'
		return state_string


class Core:
	""" 
	Maintains state for CDCL core.
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

		if num_unassigned == 1 and \
		   unassigned_lit not in self.state.model and \
		   unassigned_lit.negate() not in self.state.model:

			self.state.model.assign(unassigned_lit)
			self.graph.add_node(unassigned_lit)

			for literal in clause.literals - {unassigned_lit}:
				self.graph.add_edge(literal.negate(), unassigned_lit)

			return True
		return False

	def decide(self, literal: BoolLiteral) -> bool:
		if literal not in self.state.model and literal.negate() not in self.state.model:
			self.state.model.decide(literal)
			self.graphs.append(deepcopy(self.graph))
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
			self.state.conflict = Clause(self.graph.conflict_clause)
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

	#def learn(self) -> bool:
	#	if self.state.conflict is not None and self.state.conflict not in self.state.clauses:
	#		self.state.clauses.append(self.state.conflict)
	#		return True
	#	return False

	# TODO: store a map T[n] = {clause indices} such that if C = clause[k], k in T[n], then C has n literals x s.t. x, ~x are both unassigned

	def __repr__(self) -> str:
		core_string = 'State:\n' + repr(self.state)
		core_string += 'Implication Graph:\n' + repr(self.graph)
		return core_string