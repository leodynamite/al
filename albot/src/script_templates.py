"""
Script templates for different types of real estate
"""
from typing import Dict, Any, List
from enum import Enum
from .models import ScriptQuestion, QuestionType


class PropertyType(Enum):
    """Types of real estate"""
    NOVOSTROYKA = "novostroyka"      # Новостройка
    VTORICHKA = "vtorichka"          # Вторичка
    ARENDA = "arenda"                # Аренда
    COMMERCIAL = "commercial"        # Коммерческая
    MIXED = "mixed"                  # Смешанное


class ScriptTemplate:
    """Base script template"""
    
    def __init__(self, property_type: PropertyType, name: str, description: str):
        self.property_type = property_type
        self.name = name
        self.description = description
        self.questions = []
    
    def add_question(self, question: ScriptQuestion) -> None:
        """Add question to template"""
        self.questions.append(question)
    
    def get_script_data(self) -> Dict[str, Any]:
        """Get script data for template"""
        return {
            "name": self.name,
            "description": self.description,
            "property_type": self.property_type.value,
            "questions": [q.dict() for q in self.questions]
        }


class NovostroykaTemplate(ScriptTemplate):
    """Template for new construction properties"""
    
    def __init__(self):
        super().__init__(
            PropertyType.NOVOSTROYKA,
            "Скрипт для новостроек",
            "Оптимизированный скрипт для работы с клиентами по новостройкам"
        )
        
        # Question 1: Район
        self.add_question(ScriptQuestion(
            id="district",
            order=1,
            text="В каком районе вы рассматриваете покупку квартиры?",
            type=QuestionType.CHOICE,
            choices=["Центр", "СЗАО", "САО", "СВАО", "ВАО", "ЮВАО", "ЮАО", "ЮЗАО", "ЗАО", "Не важно"],
            mandatory=True,
            weight=25,
            hot_values=["Центр", "СЗАО", "САО"],
            purpose="Определение приоритетного района для поиска"
        ))
        
        # Question 2: Бюджет
        self.add_question(ScriptQuestion(
            id="budget",
            order=2,
            text="Какой у вас бюджет на покупку квартиры?",
            type=QuestionType.CHOICE,
            choices=["До 5 млн", "5-8 млн", "8-12 млн", "12-20 млн", "Свыше 20 млн", "Не определился"],
            mandatory=True,
            weight=30,
            hot_values=["8-12 млн", "12-20 млн", "Свыше 20 млн"],
            purpose="Оценка финансовых возможностей клиента"
        ))
        
        # Question 3: Сроки
        self.add_question(ScriptQuestion(
            id="timeline",
            order=3,
            text="Когда планируете переезжать?",
            type=QuestionType.CHOICE,
            choices=["В течение месяца", "1-3 месяца", "3-6 месяцев", "6-12 месяцев", "Пока не знаю"],
            mandatory=True,
            weight=20,
            hot_values=["В течение месяца", "1-3 месяца"],
            purpose="Определение срочности сделки"
        ))
        
        # Question 4: Ипотека
        self.add_question(ScriptQuestion(
            id="mortgage",
            order=4,
            text="Планируете ли оформлять ипотеку?",
            type=QuestionType.CHOICE,
            choices=["Да, уже одобрена", "Да, планирую оформить", "Нет, наличными", "Пока не решил"],
            mandatory=True,
            weight=15,
            hot_values=["Да, уже одобрена", "Да, планирую оформить"],
            purpose="Понимание способа оплаты"
        ))
        
        # Question 5: Специфика новостройки
        self.add_question(ScriptQuestion(
            id="new_building_specifics",
            order=5,
            text="Есть ли предпочтения по застройщику или этапу строительства?",
            type=QuestionType.TEXT,
            mandatory=False,
            weight=10,
            hot_values=["Топ-застройщик", "Готовый дом", "Сдача в этом году"],
            purpose="Уточнение специфических требований к новостройке"
        ))


class VtorichkaTemplate(ScriptTemplate):
    """Template for secondary market properties"""
    
    def __init__(self):
        super().__init__(
            PropertyType.VTORICHKA,
            "Скрипт для вторички",
            "Оптимизированный скрипт для работы с клиентами по вторичному рынку"
        )
        
        # Question 1: Район
        self.add_question(ScriptQuestion(
            id="district",
            order=1,
            text="В каком районе ищете квартиру?",
            type=QuestionType.CHOICE,
            choices=["Центр", "СЗАО", "САО", "СВАО", "ВАО", "ЮВАО", "ЮАО", "ЮЗАО", "ЗАО", "Не важно"],
            mandatory=True,
            weight=20,
            hot_values=["Центр", "СЗАО", "САО"],
            purpose="Определение района поиска"
        ))
        
        # Question 2: Бюджет
        self.add_question(ScriptQuestion(
            id="budget",
            order=2,
            text="Какой у вас бюджет на покупку?",
            type=QuestionType.CHOICE,
            choices=["До 8 млн", "8-12 млн", "12-18 млн", "18-25 млн", "Свыше 25 млн", "Не определился"],
            mandatory=True,
            weight=25,
            hot_values=["12-18 млн", "18-25 млн", "Свыше 25 млн"],
            purpose="Оценка финансовых возможностей"
        ))
        
        # Question 3: Состояние квартиры
        self.add_question(ScriptQuestion(
            id="condition",
            order=3,
            text="Какое состояние квартиры вас интересует?",
            type=QuestionType.CHOICE,
            choices=["Евроремонт", "Хорошее состояние", "Требует ремонта", "Не важно"],
            mandatory=True,
            weight=15,
            hot_values=["Евроремонт", "Хорошее состояние"],
            purpose="Понимание требований к состоянию"
        ))
        
        # Question 4: Срочность
        self.add_question(ScriptQuestion(
            id="urgency",
            order=4,
            text="Насколько срочно нужна квартира?",
            type=QuestionType.CHOICE,
            choices=["Очень срочно (до месяца)", "Срочно (1-2 месяца)", "В течение квартала", "Не спешу"],
            mandatory=True,
            weight=20,
            hot_values=["Очень срочно (до месяца)", "Срочно (1-2 месяца)"],
            purpose="Определение срочности сделки"
        ))
        
        # Question 5: Дополнительные требования
        self.add_question(ScriptQuestion(
            id="additional_requirements",
            order=5,
            text="Есть ли особые требования к квартире?",
            type=QuestionType.TEXT,
            mandatory=False,
            weight=10,
            hot_values=["Парковка", "Балкон", "Лоджия", "Консьерж"],
            purpose="Уточнение специфических требований"
        ))
        
        # Question 6: Способ оплаты
        self.add_question(ScriptQuestion(
            id="payment_method",
            order=6,
            text="Как планируете оплачивать покупку?",
            type=QuestionType.CHOICE,
            choices=["Наличными", "Ипотека", "Материнский капитал", "Смешанная оплата"],
            mandatory=True,
            weight=10,
            hot_values=["Наличными", "Ипотека"],
            purpose="Понимание способа оплаты"
        ))


class ArendaTemplate(ScriptTemplate):
    """Template for rental properties"""
    
    def __init__(self):
        super().__init__(
            PropertyType.ARENDA,
            "Скрипт для аренды",
            "Оптимизированный скрипт для работы с клиентами по аренде"
        )
        
        # Question 1: Район
        self.add_question(ScriptQuestion(
            id="district",
            order=1,
            text="В каком районе ищете квартиру для аренды?",
            type=QuestionType.CHOICE,
            choices=["Центр", "СЗАО", "САО", "СВАО", "ВАО", "ЮВАО", "ЮАО", "ЮЗАО", "ЗАО", "Не важно"],
            mandatory=True,
            weight=20,
            hot_values=["Центр", "СЗАО", "САО"],
            purpose="Определение района поиска"
        ))
        
        # Question 2: Бюджет
        self.add_question(ScriptQuestion(
            id="budget",
            order=2,
            text="Какой у вас бюджет на аренду?",
            type=QuestionType.CHOICE,
            choices=["До 50 тыс", "50-80 тыс", "80-120 тыс", "120-200 тыс", "Свыше 200 тыс"],
            mandatory=True,
            weight=25,
            hot_values=["80-120 тыс", "120-200 тыс", "Свыше 200 тыс"],
            purpose="Оценка финансовых возможностей"
        ))
        
        # Question 3: Срок аренды
        self.add_question(ScriptQuestion(
            id="rental_period",
            order=3,
            text="На какой срок планируете арендовать?",
            type=QuestionType.CHOICE,
            choices=["До 6 месяцев", "6-12 месяцев", "1-2 года", "Долгосрочно (2+ года)"],
            mandatory=True,
            weight=15,
            hot_values=["1-2 года", "Долгосрочно (2+ года)"],
            purpose="Определение срока аренды"
        ))
        
        # Question 4: Срочность
        self.add_question(ScriptQuestion(
            id="urgency",
            order=4,
            text="Когда нужна квартира?",
            type=QuestionType.CHOICE,
            choices=["Срочно (до недели)", "В течение месяца", "В течение 2-3 месяцев", "Пока не спешу"],
            mandatory=True,
            weight=20,
            hot_values=["Срочно (до недели)", "В течение месяца"],
            purpose="Определение срочности поиска"
        ))
        
        # Question 5: Состав семьи
        self.add_question(ScriptQuestion(
            id="family_composition",
            order=5,
            text="Сколько человек будет проживать?",
            type=QuestionType.CHOICE,
            choices=["1 человек", "2 человека", "Семья с детьми", "Студенты/молодые специалисты"],
            mandatory=True,
            weight=10,
            hot_values=["Семья с детьми", "2 человека"],
            purpose="Понимание состава семьи"
        ))
        
        # Question 6: Дополнительные требования
        self.add_question(ScriptQuestion(
            id="additional_requirements",
            order=6,
            text="Есть ли особые требования к квартире?",
            type=QuestionType.TEXT,
            mandatory=False,
            weight=10,
            hot_values=["Мебель", "Бытовая техника", "Парковка", "Балкон"],
            purpose="Уточнение специфических требований"
        ))


class CommercialTemplate(ScriptTemplate):
    """Template for commercial properties"""
    
    def __init__(self):
        super().__init__(
            PropertyType.COMMERCIAL,
            "Скрипт для коммерческой недвижимости",
            "Оптимизированный скрипт для работы с клиентами по коммерческой недвижимости"
        )
        
        # Question 1: Тип коммерческой недвижимости
        self.add_question(ScriptQuestion(
            id="property_type",
            order=1,
            text="Какой тип коммерческой недвижимости вас интересует?",
            type=QuestionType.CHOICE,
            choices=["Офис", "Торговое помещение", "Склад", "Производство", "Другое"],
            mandatory=True,
            weight=25,
            hot_values=["Офис", "Торговое помещение"],
            purpose="Определение типа коммерческой недвижимости"
        ))
        
        # Question 2: Район
        self.add_question(ScriptQuestion(
            id="district",
            order=2,
            text="В каком районе рассматриваете помещение?",
            type=QuestionType.CHOICE,
            choices=["Центр", "Бизнес-центры", "Торговые центры", "Промзоны", "Не важно"],
            mandatory=True,
            weight=20,
            hot_values=["Центр", "Бизнес-центры"],
            purpose="Определение района поиска"
        ))
        
        # Question 3: Площадь
        self.add_question(ScriptQuestion(
            id="area",
            order=3,
            text="Какая площадь помещения нужна?",
            type=QuestionType.CHOICE,
            choices=["До 50 кв.м", "50-100 кв.м", "100-300 кв.м", "300-1000 кв.м", "Свыше 1000 кв.м"],
            mandatory=True,
            weight=20,
            hot_values=["100-300 кв.м", "300-1000 кв.м"],
            purpose="Определение требуемой площади"
        ))
        
        # Question 4: Бюджет
        self.add_question(ScriptQuestion(
            id="budget",
            order=4,
            text="Какой у вас бюджет?",
            type=QuestionType.CHOICE,
            choices=["До 100 тыс/мес", "100-300 тыс/мес", "300-500 тыс/мес", "Свыше 500 тыс/мес"],
            mandatory=True,
            weight=25,
            hot_values=["300-500 тыс/мес", "Свыше 500 тыс/мес"],
            purpose="Оценка финансовых возможностей"
        ))
        
        # Question 5: Срочность
        self.add_question(ScriptQuestion(
            id="urgency",
            order=5,
            text="Когда нужно помещение?",
            type=QuestionType.CHOICE,
            choices=["Срочно (до месяца)", "1-3 месяца", "3-6 месяцев", "Планирую заранее"],
            mandatory=True,
            weight=10,
            hot_values=["Срочно (до месяца)", "1-3 месяца"],
            purpose="Определение срочности"
        ))


class ScriptTemplateManager:
    """Manages script templates"""
    
    def __init__(self):
        self.templates = {
            PropertyType.NOVOSTROYKA: NovostroykaTemplate(),
            PropertyType.VTORICHKA: VtorichkaTemplate(),
            PropertyType.ARENDA: ArendaTemplate(),
            PropertyType.COMMERCIAL: CommercialTemplate()
        }
    
    def get_template(self, property_type: PropertyType) -> ScriptTemplate:
        """Get template for property type"""
        return self.templates.get(property_type)
    
    def get_all_templates(self) -> Dict[PropertyType, ScriptTemplate]:
        """Get all available templates"""
        return self.templates
    
    def get_template_names(self) -> Dict[str, str]:
        """Get template names and descriptions"""
        return {
            template.property_type.value: template.name
            for template in self.templates.values()
        }
    
    def create_script_from_template(self, property_type: PropertyType, user_id: int) -> Dict[str, Any]:
        """Create script from template"""
        template = self.get_template(property_type)
        if not template:
            raise ValueError(f"No template found for property type: {property_type}")
        
        script_data = template.get_script_data()
        script_data["created_by"] = user_id
        script_data["template_type"] = property_type.value
        
        return script_data
