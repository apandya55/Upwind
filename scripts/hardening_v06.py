"""Validate the exact two post-campaign engineering changes and their AST scope."""
import ast
import hashlib
import json
from evaluate_v06 import BASE, ROOT, CONFIG, hashes

def validate_source():
    frozen=json.loads((BASE/'freeze.json').read_text())
    record=json.loads((BASE/'post-campaign-hardening.json').read_text())
    current=hashes()
    assert record['source_before']==frozen['sha256']
    assert current==record['source_after']
    assert CONFIG==frozen['config']
    changed={n for n in current if current[n]!=frozen['sha256'][n]}
    assert changed==set(record['changed_paths'])=={'backend/upwind/inference.py','backend/upwind/identifiability.py'}
    for name in changed:
        assert hashlib.sha256((BASE/'hardening-source'/name).read_bytes()).hexdigest()==current[name]
        before=ast.parse((BASE/'frozen-source'/name).read_text())
        after=ast.parse((ROOT/name).read_text())
        if name.endswith('/inference.py'):
            removed=[]
            class RemoveGuard(ast.NodeTransformer):
                def visit_If(self,node):
                    if ast.unparse(node.test)=='count * count > WEATHER_CONFIG[\'max_design_entries\']':
                        removed.append(node)
                        assert len(node.body)==1 and isinstance(node.body[0],ast.Raise)
                        assert 'Predictive target covariance exceeds numerical workload' in ast.unparse(node.body[0])
                        return None
                    return self.generic_visit(node)
            after=RemoveGuard().visit(after);assert len(removed)==1
        else:
            assert sum(isinstance(n,ast.FunctionDef) and n.name=='whiten_grouped_profile' for n in after.body)==1
            old_diagnose=next(n for n in before.body if isinstance(n,ast.FunctionDef) and n.name=='diagnose_fit')
            new_diagnose=next(n for n in after.body if isinstance(n,ast.FunctionDef) and n.name=='diagnose_fit')
            expected=ast.unparse(old_diagnose).replace(
                "signatures = signatures[c['signature_index']]\n    prof = whiten_profile(c['observed'], signatures, covariance, nuisance)",
                "prof = whiten_grouped_profile(c['observed'], signatures, covariance, nuisance, c['signature_index'])\n    else:\n        prof = whiten_profile(c['observed'], signatures, covariance, nuisance)")
            assert ast.dump(ast.parse(expected).body[0])==ast.dump(new_diagnose)
            def retained(tree):
                tree.body=[n for n in tree.body if not isinstance(n,ast.FunctionDef) or n.name not in {'whiten_grouped_profile','diagnose_fit'}]
                return tree
            before,after=retained(before),retained(after)
        assert ast.dump(before)==ast.dump(after),name
    return current

if __name__=='__main__':
    validate_source();print('Exact two-file hardening hashes, configuration and AST scope verified')
