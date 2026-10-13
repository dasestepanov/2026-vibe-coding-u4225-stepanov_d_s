"""Воспроизводимое автономное демо без Telegram и без реальных пользователей."""
import sys
import tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from service import Service
with tempfile.TemporaryDirectory() as directory:
    service = Service(Path(directory)/'demo.db')
    for command in ['/start','/add Подготовить презентацию | высокий','/add Проверить бюджет | низкий','/list','/done 1','/history','/team IT','/team Несуществующий','/feedback 4 | Тестовая запись: удобно','/stats']:
        print('> '+command+'\n'+service.execute(100,100,command)+'\n')
