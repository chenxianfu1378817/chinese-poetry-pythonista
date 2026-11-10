"""Desktop/CI JavaScript syntax gate. Not used by Pythonista at runtime."""
from pathlib import Path
import subprocess
if __name__=='__main__':
    html=(Path(__file__).resolve().parent/'poetry_app/index.html').read_text(encoding='utf-8')
    source=html.split('<script>',1)[1].split('</script>',1)[0]
    subprocess.run(['node','--check','-'],input=source,text=True,check=True)
    print('Frontend JavaScript syntax PASS')
