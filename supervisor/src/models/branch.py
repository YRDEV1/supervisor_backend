import decimal
import uuid
from sqlalchemy import LargeBinary, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from supervisor.src.core.database import Base

class Branch(Base):
    __tablename__ = "_reference1054"

    # --- Identity & hierarchy -------------------------------------------------
    id: Mapped[bytes] = mapped_column("_idrref", LargeBinary(16), primary_key=True)
    version: Mapped[int] = mapped_column("_version")
    is_marked_for_deletion: Mapped[bool] = mapped_column("_marked")
    predefined_id: Mapped[bytes] = mapped_column("_predefinedid", LargeBinary(16))
    parent_id: Mapped[bytes] = mapped_column("_parentidrref", LargeBinary(16))
    is_group: Mapped[bool] = mapped_column("_folder")
    code: Mapped[decimal.Decimal] = mapped_column("_code", Numeric)
    full_name: Mapped[str] = mapped_column("_description")

    # --- Currency / print settings ------------------------------------------------
    sales_currency_type_ref: Mapped[bytes] = mapped_column("_fld1339rref", LargeBinary(16))  # ПродажТипВалюта
    purchase_currency_ref: Mapped[bytes] = mapped_column("_fld3665rref", LargeBinary(16))  # ПриходКилишВалютаси
    sales_currency_ref: Mapped[bytes] = mapped_column("_fld3774rref", LargeBinary(16))  # СавдоКилишВалютаси

    sales_print_type_ref: Mapped[bytes] = mapped_column("_fld2211rref", LargeBinary(16))  # ТипПечатьПродаж
    agent_sales_print_type_ref: Mapped[bytes] = mapped_column("_fld5184rref", LargeBinary(16))  # ТипПечатьПродажАгент
    payment_print_type_ref: Mapped[bytes] = mapped_column("_fld4183rref", LargeBinary(16))  # ТипПечатьТолов
    print_type_ref: Mapped[bytes] = mapped_column("_fld2213rref", LargeBinary(16))  # ТипПечать
    cash_print_type_ref: Mapped[bytes] = mapped_column("_fld4184rref", LargeBinary(16))  # ТипПечатьКасса

    check_id_name: Mapped[str] = mapped_column("_fld2203")  # ЧекИдНаим
    check_company_ref: Mapped[bytes] = mapped_column("_fld4051rref", LargeBinary(16))  # ЧекФирма
    virtual_cashbox_info: Mapped[str] = mapped_column("_fld6411")  # ИнформацияВиртуалКасса

    # --- Linked catalog references ------------------------------------------------
    employee_ref: Mapped[bytes] = mapped_column("_fld2257rref", LargeBinary(16))  # Сотрудник
    user_ref: Mapped[bytes] = mapped_column("_fld2258rref", LargeBinary(16))  # Пользователь

    # --- Percentages / numeric settings --------------------------------------------
    return_cash_deposit_percent: Mapped[decimal.Decimal] = mapped_column("_fld1718", Numeric)  # ВозвратдаНахТушишФоиз
    employee_fine_percent: Mapped[decimal.Decimal] = mapped_column("_fld5185", Numeric)  # ХодимЖаримаФоизда

    # --- Feature toggle flags -------------------------------------------------------
    has_mixed_sales: Mapped[bool] = mapped_column("_fld1550")  # АралашСавдоМавжуд
    has_local_app: Mapped[bool] = mapped_column("_fld1585")  # ЛосалПриложенияМавжуд
    is_main_cashbox_for_branch: Mapped[bool] = mapped_column("_fld3775")  # БуФилиалБошКасса
    has_simple_production: Mapped[bool] = mapped_column("_fld3666")  # СоддаИшлабЧикаришМавжуд
    has_crushing_production: Mapped[bool] = mapped_column("_fld4300")  # ДрабилкаИшлабЧикаришМавжуд (name truncated in 1C)
    has_distribution: Mapped[bool] = mapped_column("_fld4693")  # ДистрибюцияМавжуд
    has_distributor_sub_client: Mapped[bool] = mapped_column("_fld5187")  # ДистрСубКлиентМавжуд
    has_distributor_onesell: Mapped[bool] = mapped_column("_fld5869")  # ДистрдаOneSellМавжуд
    can_sell_to_other_branch: Mapped[bool] = mapped_column("_fld4471")  # БошкаФилиалгаСотишИмкон... (name truncated in 1C)
    is_revision_enabled: Mapped[bool] = mapped_column("_fld2641")  # Ревизия

    # --- Unclear / truncated flags (kept 1:1, meaning not confirmed) --------------
    employee_mobile_start_balance_flag: Mapped[bool] = mapped_column("_fld1581")  # ХодимМобилНачОстдаПрих... (name truncated in 1C)
    value_entry_window_flag: Mapped[bool] = mapped_column("_fld2390")  # КийматКиритадиганОйнадаС... (name truncated in 1C)
    employee_salary_by_time_flag: Mapped[bool] = mapped_column("_fld2512")  # ХодимОйлигиВактБойичаХи... (name truncated in 1C)
    employee_linked_to_directory_flag: Mapped[bool] = mapped_column("_fld2580")  # СотрудникСправичнигигаБи... (name truncated in 1C)
    no_seller_employee_flag: Mapped[bool] = mapped_column("_fld2671")  # БезПродавецСотрудникСот... (name truncated in 1C)
    on_document_confirm_flag: Mapped[bool] = mapped_column("_fld2687")  # ДокументларТасдикланганда... (name truncated in 1C)
    sell_via_other_branches_flag: Mapped[bool] = mapped_column("_fld2696")  # БуФилиалдаПрочиФилиалОр... (name truncated in 1C)
    price_quantity_entry_window_flag: Mapped[bool] = mapped_column("_fld2705")  # НархВаСонКиритишОйнасид... (name truncated in 1C)
    dollar_entry_in_sales_window_flag: Mapped[bool] = mapped_column("_fld2706")  # СавдоОйнасидаДолларКири... (name truncated in 1C)
    not_sold_from_this_branch_flag: Mapped[bool] = mapped_column("_fld3619")  # БуФилиалданСавдоКилинма... (name truncated in 1C)
    direct_sales_window_flag: Mapped[bool] = mapped_column("_fld3620")  # СавдоОйнадаТугриданТугри... (name truncated in 1C)
    simple_production_cost_flag: Mapped[bool] = mapped_column("_fld3667")  # СоддаИшлабЧикаришТаннар... (name truncated in 1C)
    simple_production_employee_flag: Mapped[bool] = mapped_column("_fld3668")  # СоддаИшлабЧикаришдаХод... (name truncated in 1C)
    simple_production_flag_4299: Mapped[bool] = mapped_column("_fld4299")  # СоддаИшлабЧикаришдаРас... (name truncated in 1C)
    simple_production_product_flag: Mapped[bool] = mapped_column("_fld4052")  # СоддаИшлабЧикаришдаПро... (name truncated in 1C)
    simple_production_calc_flag: Mapped[bool] = mapped_column("_fld4470")  # СоддаИшлабЧикаришдаКалк... (name truncated in 1C)
    no_calculation_production_flag_1: Mapped[bool] = mapped_column("_fld4053")  # БезКалкуляцияИшлабЧикари... (name truncated in 1C)
    no_calculation_production_flag_2: Mapped[bool] = mapped_column("_fld4054")  # БезКалкуляцияИшлабЧикари... (name truncated in 1C)
    no_calculation_production_flag_3: Mapped[bool] = mapped_column("_fld4055")  # БезКалкуляцияИшлабЧикари... (name truncated in 1C)
    crushing_production_cost_flag: Mapped[bool] = mapped_column("_fld4301")  # ДрабилкаИшлабЧикаришТан... (name truncated in 1C)
    crushing_production_employee_flag: Mapped[bool] = mapped_column("_fld4302")  # ДрабилкаИшлабЧикаришдаХ... (name truncated in 1C)
    simple_courier_app_flag: Mapped[bool] = mapped_column("_fld4411")  # ОддийДоставшикПриложени... (name truncated in 1C)
    multiple_couriers_flag: Mapped[bool] = mapped_column("_fld5186")  # ДоставшикларСониБирданО... (name truncated in 1C)
    distributor_barcode_flag: Mapped[bool] = mapped_column("_fld5188")  # ДистрдаТоварШтрихКодБой... (name truncated in 1C)

    def __repr__(self) -> str:
        return f"<Branch code={self.code!r} name={self.full_name!r}>"
