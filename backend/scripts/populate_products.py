from sqlmodel import create_engine, Session
from app.models.product import Product

# Данные для заполнения
products_data = [
    {
        "name": "Труба металлическая",
        "description": "Труба из нержавеющей стали, диаметр 50мм",
        "price": 1500.0,
        "quantity": 100
    },
    {
        "name": "Труба пластиковая",
        "description": "Полипропиленовая труба, диаметр 32мм",
        "price": 250.0,
        "quantity": 200
    },
    {
        "name": "Фитинг",
        "description": "Угловой фитинг 90 градусов, диаметр 32мм",
        "price": 45.0,
        "quantity": 500
    },
    {
        "name": "Клапан",
        "description": "Обратный клапан, диаметр 50мм",
        "price": 1200.0,
        "quantity": 50
    }
]

def main():
    # Создаем подключение к базе данных
    # Используем имя сервиса db вместо localhost для подключения из контейнера
    DATABASE_URL = "postgresql://postgres:postgres@db:5432/b2b"
    engine = create_engine(DATABASE_URL)
    
    # Создаем таблицу, если она не существует
    Product.metadata.create_all(engine)
    
    # Создаем сессию
    with Session(engine) as session:
        # Добавляем каждый продукт в базу данных
        for product_data in products_data:
            product = Product(**product_data)
            session.add(product)
        
        # Сохраняем изменения
        session.commit()
    
    print("Тестовые товары успешно добавлены в базу данных!")

if __name__ == "__main__":
    main() 