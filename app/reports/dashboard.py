# app/reports/dashboard.py
from dash import Dash, html, dcc, Input, Output
import pandas as pd

# Данные для примера
data = pd.DataFrame({
    'region': ['Регион 1', 'Регион 2', 'Регион 3'],
    'rating': [4.5, 3.2, 2.8],
    'country_rank': [3, 15, 45],
    'macro_rank': [1, 5, 12]
})

# Интерпретации оценок
interpretations = {
    (1.0, 2.0): "Туристская инфраструктура слабо развита, требуется значительное улучшение.",
    (2.1, 3.0): "Средний уровень, подходит для локальных туристов, но имеет ограничения для международного туризма.",
    (3.1, 4.0): "Хорошая инфраструктура, пригодная для национальных и международных туристов.",
    (4.1, 5.0): "Высокий уровень инфраструктуры, готовый к приему большого турпотока и международных мероприятий."
}

# Вспомогательная функция для интерпретации
def get_interpretation(rating):
    for (low, high), text in interpretations.items():
        if low <= rating <= high:
            return text
    return "Нет данных."

def create_dashboard(flask_server):
    app_dash = Dash(
        __name__,
        server=flask_server,
        url_base_pathname='/dashboard/',
        suppress_callback_exceptions=True  # Добавьте, если есть динамические компоненты
    )

    # Главный layout дашборда
    app_dash.layout = html.Div([
        html.H1("Комплексная оценка туристской отрасли регионов"),

        # Дропдаун для выбора региона
        dcc.Dropdown(
            id='region-dropdown',
            options=[{'label': row['region'], 'value': index} for index, row in data.iterrows()],
            value=0
        ),

        # Блок оценки
        html.Div(id='rating-display'),

        # Детальный расчет
        html.Div(id='detailed-calculation', style={'margin-top': '20px'})
    ])

    # Обновление оценки и рейтинга
    @app_dash.callback(
        [Output('rating-display', 'children'),
         Output('detailed-calculation', 'children')],
        Input('region-dropdown', 'value')
    )
    def update_dashboard(selected_region):
        region = data.iloc[selected_region]
        rating = region['rating']

        # Генерация звезд
        stars = '★' * int(rating) + '☆' * (5 - int(rating))

        # Описание и позиции
        description = get_interpretation(rating)
        country_rank = f"Место в стране: {region['country_rank']}"
        macro_rank = f"Место в макрорегионе: {region['macro_rank']}"

        # Пример расчета
        detailed = html.Pre(f"""
        Подробный расчет:
        Ttotal = 0.4 * 4.2 + 0.2 * 4.0 + 0.1 * 4.5 + 0.1 * 4.3 + 0.05 * 4.1 + 0.05 * 3.8 + 0.05 * 3.9 + 0.05 * 4.0
               = {rating:.2f}
        """)

        return [
            html.Div([
                html.H2(f"Рейтинг: {rating:.1f} {stars}"),
                html.P(description),
                html.P(country_rank),
                html.P(macro_rank)
            ]),
            detailed
        ]

    return app_dash