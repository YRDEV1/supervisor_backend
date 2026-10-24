import datetime
import decimal
import uuid
from sqlalchemy import LargeBinary, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from supervisor.src.core.database import Base
from supervisor.src.models.core import MVARCHAR

class Employee(Base):
    """A row in the Employees catalog (`_reference1109`).

    Attribute names below are transcribed from the 1C configurator's field
    list for Справочник.Сотрудник (mixed Russian/Uzbek). Fields whose 1C
    label was cut off in that list are marked "(name truncated in 1C)" -
    their Python name is a best guess and the meaning is unconfirmed.
    """

    __tablename__ = "_reference1109"

    # --- Identity & hierarchy -------------------------------------------------
    id: Mapped[bytes] = mapped_column("_idrref", LargeBinary(16), primary_key=True)
    version: Mapped[int] = mapped_column("_version")
    is_marked_for_deletion: Mapped[bool] = mapped_column("_marked")
    predefined_id: Mapped[bytes] = mapped_column("_predefinedid", LargeBinary(16))

    # Points at another row in this same table: either a role group node
    # (ТП / СВ / ДСТ / ОХР) or, for some entries, another employee.
    parent_id: Mapped[bytes] = mapped_column("_parentidrref", LargeBinary(16))

    # True for role-group nodes and for some employees that themselves group
    # sub-entries (observed on several "СВ" rows) - not a strict is-a-role flag.
    is_group: Mapped[bool] = mapped_column("_folder")

    code: Mapped[decimal.Decimal] = mapped_column("_code", Numeric)
    full_name: Mapped[str] = mapped_column("_description")

    # --- Contact info ----------------------------------------------------------
    phone: Mapped[str] = mapped_column("_fld1117")  # Тел
    address: Mapped[str] = mapped_column("_fld1118")  # Адрес
    inn: Mapped[str] = mapped_column("_fld1119")  # Инн
    birth_date: Mapped[datetime.datetime] = mapped_column("_fld2216")  # ДеньРождения

    # --- App/login credentials --------------------------------------------------
    login: Mapped[str] = mapped_column("_fld1553", MVARCHAR())  # Логин
    password: Mapped[str] = mapped_column("_fld1554", MVARCHAR())  # Парол
    bot_token: Mapped[bytes] = mapped_column("_fld1556", LargeBinary(16))  # Б_Токен
    is_registered: Mapped[bool] = mapped_column("_fld1697")  # Регистрация
    external_id: Mapped[str] = mapped_column("_fld1705")  # Ид

    # --- Photo -------------------------------------------------------------------
    photo_url: Mapped[str] = mapped_column("_fld2591")  # АдресКартинки
    photo_filename: Mapped[str] = mapped_column("_fld2592")  # ИмяКартинки

    # --- Work schedule -----------------------------------------------------------
    default_shift_start: Mapped[datetime.datetime] = mapped_column("_fld2503")  # НачВремя
    default_shift_end: Mapped[datetime.datetime] = mapped_column("_fld2504")  # КонВремя
    default_shift_hours: Mapped[decimal.Decimal] = mapped_column("_fld2505", Numeric)  # РабочееВремя

    custom_shift_start: Mapped[datetime.datetime] = mapped_column("_fld5196")  # ЛосацияНачВремя
    custom_shift_end: Mapped[datetime.datetime] = mapped_column("_fld5197")  # ЛосацияКонВремя
    has_custom_shift: Mapped[bool] = mapped_column("_fld5198")  # Лосация

    monthly_salary: Mapped[decimal.Decimal] = mapped_column("_fld2513", Numeric)  # ОйликСумма
    monthly_working_days: Mapped[decimal.Decimal] = mapped_column("_fld2514", Numeric)  # БелгиланганОйликКун
    location_range_meters: Mapped[decimal.Decimal] = mapped_column("_fld5451", Numeric)  # ДиапазонМетр

    auto_detect_workday: Mapped[bool] = mapped_column("_fld4060")  # ИшКуниАвтоАниклаш
    rests_on_sunday: Mapped[bool] = mapped_column("_fld4061")  # ЯкшанбаДамОлади

    # --- Linked catalog references ------------------------------------------------
    # _fld1116rref and _fld4481rref are always equal in observed data.
    branch_ref: Mapped[bytes] = mapped_column("_fld1116rref", LargeBinary(16))  # Филиалы
    salary_branch_ref: Mapped[bytes] = mapped_column("_fld4481rref", LargeBinary(16))  # ФилиалыЗарплата

    gender_ref: Mapped[bytes] = mapped_column("_fld2273rref", LargeBinary(16))  # СотрудникПол
    user_ref: Mapped[bytes] = mapped_column("_fld2274rref", LargeBinary(16))  # Пользователь

    # --- Unidentified fields (kept 1:1, meaning not confirmed) ------------------
    text_1539: Mapped[str] = mapped_column("_fld1539")  # ПараллелСклад

    # --- Role flags ---------------------------------------------------------------
    is_sales_supplier: Mapped[bool] = mapped_column("_fld1353")  # ПродажПоставщик
    is_agent: Mapped[bool] = mapped_column("_fld4703")  # Агент
    is_courier: Mapped[bool] = mapped_column("_fld4704")  # Доставщик
    is_courier_secondary: Mapped[bool] = mapped_column("_fld6355")  # Доставщик2
    is_supervisor: Mapped[bool] = mapped_column("_fld5362")  # Супервизор
    is_merchandiser: Mapped[bool] = mapped_column("_fld5363")  # Мерчандайзер

    # --- Permission / capability flags --------------------------------------------
    can_edit: Mapped[bool] = mapped_column("_fld1532")  # Изменить
    can_open: Mapped[bool] = mapped_column("_fld1533")  # Открыть
    can_delete: Mapped[bool] = mapped_column("_fld1534")  # Удалить
    can_view_history: Mapped[bool] = mapped_column("_fld1535")  # ИсторияВидимость
    can_view_cart: Mapped[bool] = mapped_column("_fld1536")  # КорзинаВидимость
    can_edit_branches: Mapped[bool] = mapped_column("_fld1537")  # ФилиалыИзминить
    can_view_purchase_price: Mapped[bool] = mapped_column("_fld1538")  # ПриходЦенаВидимость
    can_close_deal: Mapped[bool] = mapped_column("_fld1555")  # ДелоЗакрыть
    is_test_account: Mapped[bool] = mapped_column("_fld2502")  # Тест
    can_view_purchase_confirmation: Mapped[bool] = mapped_column("_fld2205")  # ПриходТасдиклашВидимость
    has_personal_cash_register: Mapped[bool] = mapped_column("_fld2382")  # ДоступенЛичныйКасса
    can_confirm_cash_transfer: Mapped[bool] = mapped_column("_fld2383")  # ПеремешенияДенегТасдикл... (name truncated in 1C)
    can_confirm_goods_transfer: Mapped[bool] = mapped_column("_fld2440")  # ПеремешенияТоварТасдикл... (name truncated in 1C)
    can_view_last_purchase_price_in_sales: Mapped[bool] = mapped_column("_fld2688")  # СавдодаОхиргиПриходНарх... (name truncated in 1C)
    is_used_in_bdm_report: Mapped[bool] = mapped_column("_fld4059")  # БДМРепортданФойдаланилад... (name truncated in 1C)
    local_app_flag_1: Mapped[bool] = mapped_column("_fld4414")  # ЛосалПриложениядаХодимг... (name truncated in 1C)
    local_app_flag_2: Mapped[bool] = mapped_column("_fld4415")  # ЛосалПриложениядаХодим... (name truncated in 1C)
    show_product_in_sales_window: Mapped[bool] = mapped_column("_fld4464")  # СавдоОйнасидаМахсулотни... (name truncated in 1C)
    distributor_app_client_flag: Mapped[bool] = mapped_column("_fld5195")  # ДистрПриложениядаКлиентК... (name truncated in 1C)
    distributor_client_save_flag: Mapped[bool] = mapped_column("_fld5199")  # ДистрдаКлиентСаклашдаСу... (name truncated in 1C)
    can_change_agent_in_app: Mapped[bool] = mapped_column("_fld5448")  # ДастурдаАгентниУзгартира... (name truncated in 1C)
    can_edit_client_location: Mapped[bool] = mapped_column("_fld5530")  # ИзминитьКлиентЛосацион
    has_unrestricted_edit: Mapped[bool] = mapped_column("_fld5741")  # БезОграниченияИзменитьО... (name truncated in 1C)
    onesell_enabled: Mapped[bool] = mapped_column("_fld5867")  # OneSell
    can_view_distributor_returns: Mapped[bool] = mapped_column("_fld5978")  # ДистВозвратВидимость
    can_create_client: Mapped[bool] = mapped_column("_fld6272")  # СоздатКлиент
    can_edit_sales_price: Mapped[bool] = mapped_column("_fld6273")  # ИзминитьПродажЦена
    can_view_operator_window: Mapped[bool] = mapped_column("_fld6274")  # ОператорОкноВидимостьУд... (name truncated in 1C)
    can_edit_client_data: Mapped[bool] = mapped_column("_fld6276")  # ИзменениеДанныхКлиента

    # --- Dashboard visibility flags -------------------------------------------------
    dashboard_sales_visibility_1: Mapped[bool] = mapped_column("_fld1991")  # ВидимостьДашбордПродаж... (name truncated in 1C)
    dashboard_sales_visibility_2: Mapped[bool] = mapped_column("_fld1992")  # ВидимостьДашбордПродаж... (name truncated in 1C)
    dashboard_sales_visibility_3: Mapped[bool] = mapped_column("_fld1993")  # ВидимостьДашбордПродаж... (name truncated in 1C)
    dashboard_sales_visibility_4: Mapped[bool] = mapped_column("_fld2208")  # ВидимостьДашбордПродаж... (name truncated in 1C)
    dashboard_min_quantity_visibility: Mapped[bool] = mapped_column("_fld2209")  # ВидимостьДашбоардМинКо... (name truncated in 1C)
    dashboard_reserved_visibility: Mapped[bool] = mapped_column("_fld2217")  # ВидимостьДашбоардБронД... (name truncated in 1C)
    dashboard_product_visibility: Mapped[bool] = mapped_column("_fld2218")  # ВидимостьДашбоардТовар... (name truncated in 1C)
    dashboard_admin_visibility: Mapped[bool] = mapped_column("_fld2542")  # ВидимостьДашбоардАдмин
    dashboard_branch_visibility: Mapped[bool] = mapped_column("_fld2543")  # ВидимостьДашбоардФилиал
    dashboard_rating_visibility: Mapped[bool] = mapped_column("_fld2544")  # ВидимостьДашбоардРейтинг... (name truncated in 1C)
    dashboard_stock_visibility: Mapped[bool] = mapped_column("_fld4233")  # ВидимостьДашбордЗапасТо... (name truncated in 1C)

    # --- Rating / evaluation ----------------------------------------------------
    has_rating: Mapped[bool] = mapped_column("_fld2545")  # Рейтинг
    is_evaluation_enabled: Mapped[bool] = mapped_column("_fld2590")  # Бахолаш

    def __repr__(self) -> str:
        return f"<Employee code={self.code!r} name={self.full_name!r}>"


# Role-group node ids inside `_reference1109` - not separate rows in another
# table. See DATA/SUPERVISORS.md.
ROLE_SALES_REP = uuid.UUID("a73a0050-5607-0e09-11f0-4f17e018d4c6")  # ТП
ROLE_SUPERVISOR = uuid.UUID("a73a0050-5607-0e09-11f0-50e1332c7fcd")  # СВ
ROLE_LOGISTICS = uuid.UUID("a73a0050-5607-0e09-11f0-50e1a458d35f")  # ДСТ
ROLE_SECURITY = uuid.UUID("a73a0050-5607-0e09-11f0-50e240952b2e")  # ОХР
