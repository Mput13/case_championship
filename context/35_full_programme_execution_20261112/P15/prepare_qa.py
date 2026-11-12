from pathlib import Path
P=Path(__file__).resolve().parent
page=(P/'dashboard_candidate.html').read_text()
(P/'qa/interaction.html').write_text(page.replace('</body>','<script>'+(P/'qa/interaction.js').read_text()+'</script></body>'))
for name,ids in [('network',['network']),('strategy',['strategy']),('direct',['direct'])]:
    css='main>section:not('+','.join('#'+s for s in ids)+'){display:none}.context,.tourbar{display:none}'
    (P/f'qa/{name}.html').write_text(page.replace('</head>',f'<style>{css}</style></head>'))
(P/'qa/source.html').write_text(page.replace('</body>','<script>chooseCity("GOJ");researchSource("evidence","0");</script></body>'))
css='main>section:not(#hubs){display:none}.context,.tourbar,.hero{display:none}#hubs>:not(.card:has(#monthly-source-evidence)){display:none}'
(P/'qa/monthly-vvo.html').write_text(page.replace('</head>',f'<style>{css}</style></head>').replace('</body>','<script>chooseCity("VVO");$("monthly-source-evidence").parentElement.open=true;$("monthly-source-evidence").querySelector("details").open=true;</script></body>'))
