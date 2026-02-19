from core import *

if __name__ == '__main__':
	state = State([Clause.make("1"), Clause.make("-1", "2"), Clause.make("-3", "4"), Clause.make("-5", "-6"), Clause.make("-1", "-5", "7"), Clause.make("-2", "-5", "6", "-7")])
	core = Core(state)
	core.propagate(0)
	core.propagate(1)
	core.decide(BoolLiteral.make_pos("3"))
	core.propagate(2)
	core.decide(BoolLiteral.make_pos("5"))
	core.propagate(3)
	core.propagate(4)
	core.conflict(5)
	print(core)
	core.explain()
	print(core)
	core.backjump(0)
	print(core)