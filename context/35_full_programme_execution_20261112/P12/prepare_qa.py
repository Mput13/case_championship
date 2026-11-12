from pathlib import Path
P=Path(__file__).resolve().parent
page=(P/'ui_candidate/dashboard.html').read_text()
(P/'qa/interaction.html').write_text(page.replace('</body>','<script>'+ (P/'qa/interaction.js').read_text()+'</script></body>'))
for name,sections in [('network', ['network','strategy']),('hubs',['hubs']),('direct',['direct'])]:
 css='main>section:not('+','.join('#'+s for s in sections)+'){display:none} .context,.tourbar{display:none}'
 (P/f'qa/{name}.html').write_text(page.replace('</head>',f'<style>{css}</style></head>'))

(P/'qa/source.html').write_text(page.replace('</body>','<script>RW.chooseCity(\"GOJ\"); RW.source(\"product\",RW.offers()[0].product_id);</script></body>'))

(P/'qa/errors.html').write_text(page.replace('</body>','<script>'+(P/'qa/errors.js').read_text()+'</script></body>'))
