#!/usr/bin/env python3
"""Test document generation."""

from datetime import datetime
from app.services.document_generator import DocumentGenerator

# Create generator
gen = DocumentGenerator()

# Test data
listeners = [
    {
        'full_name': 'Беляева Евгения Алексеевна',
        'position': 'Администратор',
        'court_name': 'Управление Судебного департамента в Карачаево-Черкесской Республике',
        'region': 'Карачаево-Черкесская Республика'
    },
    {
        'full_name': 'Канаматов Мурат Борисович',
        'position': 'Администратор',
        'court_name': 'Управление Судебного департамента в Карачаево-Черкесской Республике',
        'region': 'Карачаево-Черкесская Республика'
    },
    {
        'full_name': 'Лайпанов Исхак Исмаилович',
        'position': 'Администратор',
        'court_name': 'Управление Судебного департамента в Карачаево-Черкесской Республике',
        'region': 'Карачаево-Черкесская Республика'
    },
]

# Generate enrollment order
result = gen.generate_order(
    order_type='enrollment',
    listeners_data=listeners,
    order_number='111',
    order_date=datetime(2025, 11, 12),
    program_name='Государственная гражданская служба',
    stream_name='государственных гражданских служащих',
    start_date=datetime(2025, 11, 12),
    end_date=datetime(2025, 11, 18),
    contract_date='28 мая 2025 года',
)
print(f'✓ Приказ о зачислении: {result}')

# Generate admission order
result2 = gen.generate_order(
    order_type='admission',
    listeners_data=listeners,
    order_number='114',
    order_date=datetime(2025, 11, 18),
    program_name='Государственная гражданская служба',
    stream_name='государственных гражданских служащих',
)
print(f'✓ Приказ о допуске: {result2}')

# Generate graduation order
result3 = gen.generate_order(
    order_type='graduation',
    listeners_data=listeners,
    order_number='115',
    order_date=datetime(2025, 11, 20),
    program_name='Государственная гражданская служба',
    stream_name='государственных гражданских служащих',
    contract_date='28 мая 2025 года',
    hours=16,
)
print(f'✓ Приказ об отчислении: {result3}')

print()
print('Все документы успешно сгенерированы!')
