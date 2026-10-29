import time
from datetime import timedelta

t_start = time.time()
time.sleep(5)

# Считаем разницу (она будет положительной)
elapsed = time.time() - t_start

# Превращаем секунды в понятный формат длительности
duration = timedelta(seconds=elapsed)

print(duration)  # Выведет: 0:00:05.005123 (часы:минуты:секунды)