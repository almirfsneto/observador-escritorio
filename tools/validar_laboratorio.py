"""Source-checkout launcher, without pip, downloads, shell policy changes or installation."""
from pathlib import Path
import sys

repository = Path(__file__).resolve().parents[1]
if sys.version_info < (3, 11):
    raise SystemExit('É necessário Python 3.11 ou superior, previamente instalado.')
sys.path.insert(0, str(repository / 'src'))
from observador.acceptance_wizard import main

if __name__ == '__main__':
    main(repository)
