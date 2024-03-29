echo "Текущая рабочая директория:"
pwd
read -r -p "Этот скрипт необходимо запускать из корня проекта. Убедитесь, что он работает откуда должен"

read -r -p "устанавливаем системную утилиту для создания окружений и доп. интерпретатор версии 3.9"
sudo apt-get install python3-venv python3.9
if [ -d "venv" ]; then
  echo "виртуальное окружение уже существует"
else
  read -r -p "создаём окружение с нужной версией питона"
  virtualenv venv --python=python3.9
fi
read -r -p "активируем виртуальное окружение"
. venv/bin/activate
which pip
read -r -p "смотрим где находится pip (если всё хорошо, то он должен быть где-то в папке с проектом, а не в системных папках)"
which python
read -r -p "смотрим где находится python (если всё хорошо, то он должен быть где-то в папке с проектом, а не в системных папках)"
python -V
read -r -p "смотрим версию питона. Должна быть 3.9.+"
read -r -p "ставим зависимости внутри окружения"
pip install -r requirements.txt
# зависимость, которая почему-то не ставится через requirements.txt
pip install dependency_injector[yaml]
if [ -d "venv" ]; then
  read -r -p "конфиг запуска уже существует"
else
  read -r -p "конфиг запуска не найден - копируем шаблонный конфиг"
  cp sample_config.yaml config.yaml
fi