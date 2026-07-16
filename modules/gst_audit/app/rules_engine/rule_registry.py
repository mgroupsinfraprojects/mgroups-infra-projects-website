class RuleRegistry:
    def __init__(self): self.rules={}
    def register(self, name, version, fn): self.rules[name] = {"version": version, "fn": fn}
    def run(self, name, row): return self.rules[name]["fn"](row)
