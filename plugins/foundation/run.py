"""Foundation plugin: the original prep stage (site, products, official facts, checks)."""
from seolib.prep import prep


def run(ctx):
    prep(ctx.brief["_path"], ctx.refresh, quiet=True, timing=False)
    sheet = ctx.load("foundation")["sheet"]
    n = sum(1 for f in sheet.get("facts", []) if f.get("status") in ("verified", "captured"))
    return {"summary": f"{n} verified facts, {len(sheet.get('products', []))} products, page {sheet.get('page', {}).get('status')}"}
