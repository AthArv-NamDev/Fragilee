import sys, subprocess, weasyprint
f, h = sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 2400
css = weasyprint.CSS(string=f"@page{{size:1200px {h}px;margin:0}} body{{width:1200px}}")
weasyprint.HTML(f).write_pdf("/tmp/r.pdf", stylesheets=[css])
subprocess.run(["pdftoppm", "-png", "-r", "72", "-f", "1", "-l", "1", "/tmp/r.pdf", "/tmp/r"], check=True)
