"""Обработчики воронки регистрации."""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.states import RegistrationStates
from app.bot.keyboards.reply import get_phone_keyboard, remove_keyboard
from app.bot.keyboards.inline import get_main_menu_keyboard
from app.bot.utils.messages import Messages
from app.services.validation import validate_email, validate_name, validate_phone
from app.database.crud import get_or_create_user, update_user_payment_status, mark_google_sheet_sent
from app.services.subscription import get_or_create_subscription, check_user_access
from app.config import settings
from app.utils.logger import logger

router = Router()


@router.message(RegistrationStates.GET_NAME)
async def process_name(message: Message, state: FSMContext):
    """
    Обработка ввода имени пользователя.
    
    Валидирует имя и переходит к запросу email.
    """
    name = message.text.strip()
    
    if not validate_name(name):
        await message.answer(
            Messages.error_invalid_name(),
            parse_mode="HTML"
        )
        return
    
    # Сохраняем имя в FSM
    await state.update_data(name=name)
    await state.set_state(RegistrationStates.GET_EMAIL)
    
    logger.info(f"User entered name: telegram_id={message.from_user.id}, name={name}")
    
    await message.answer(
        Messages.registration_step_email(name, step=2),
        parse_mode="HTML"
    )


@router.message(RegistrationStates.GET_EMAIL)
async def process_email(message: Message, state: FSMContext):
    """
    Обработка ввода email пользователя.
    
    Валидирует email и переходит к запросу телефона.
    """
    email = message.text.strip()
    
    if not validate_email(email):
        await message.answer(
            Messages.error_invalid_email(),
            parse_mode="HTML"
        )
        return
    
    # Сохраняем email в FSM
    await state.update_data(email=email)
    await state.set_state(RegistrationStates.GET_PHONE)
    
    logger.info(f"User entered email: telegram_id={message.from_user.id}, email={email}")
    
    await message.answer(
        Messages.registration_step_phone(step=3),
        parse_mode="HTML",
        reply_markup=get_phone_keyboard()
    )


@router.message(RegistrationStates.GET_PHONE, F.contact)
async def process_phone_contact(message: Message, state: FSMContext, session: AsyncSession):
    """
    Обработка номера телефона через кнопку Telegram.
    
    Получает контакт от пользователя и завершает регистрацию.
    """
    phone = message.contact.phone_number
    
    logger.info(f"User shared contact: telegram_id={message.from_user.id}, phone={phone}")
    
    await complete_registration(message, state, session, phone)


@router.message(RegistrationStates.GET_PHONE)
async def process_phone_text(message: Message, state: FSMContext, session: AsyncSession):
    """
    Обработка номера телефона через текстовый ввод.
    
    Валидирует телефон и завершает регистрацию.
    """
    phone = validate_phone(message.text)
    
    if not phone:
        await message.answer(
            Messages.error_invalid_phone(),
            parse_mode="HTML"
        )
        return
    
    logger.info(f"User entered phone: telegram_id={message.from_user.id}, phone={phone}")
    
    await complete_registration(message, state, session, phone)


async def complete_registration(
    message: Message, 
    state: FSMContext, 
    session: AsyncSession, 
    phone: str
):
    """
    Завершение процесса регистрации.
    
    Сохраняет пользователя в БД и выдает ссылку на таблицу.
    """
    # Получаем данные из FSM
    data = await state.get_data()
    telegram_id = message.from_user.id
    
    try:
        # Получаем или создаем пользователя (безопасно от race condition)
        user, was_created = await get_or_create_user(
            session=session,
            telegram_id=telegram_id,
            name=data['name'],
            email=data['email'],
            phone=phone
        )
        
        # Если пользователь уже существовал, обновляем его данные
        if not was_created:
            logger.info(f"User already exists, updating data: telegram_id={telegram_id}")
            # Обновляем только если данные изменились
            if user.full_name != data['name'] or user.email != data['email'] or user.phone != phone:
                user.full_name = data['name']
                user.email = data['email']
                user.phone = phone
                await session.commit()
                await session.refresh(user)
        else:
            logger.info(f"New user created: telegram_id={telegram_id}")
        
        # ============================================
        # [ТОЧКА ИНТЕГРАЦИИ ПЛАТЕЖЕЙ - FEATURE FLAG]
        # ============================================
        # Создаем или получаем подписку пользователя
        subscription = await get_or_create_subscription(user.id, session)
        
        # Проверяем включены ли платежи
        if settings.payment_enabled:
            # ПРОДАКШН: Отправляем инвойс для оплаты
            # TODO: Реализовать send_payment_invoice()
            # await send_payment_invoice(message, user, subscription)
            # await state.set_state(RegistrationStates.PAYMENT_PENDING)
            # return
            
            # Пока платежи не реализованы - даем триал
            logger.info(f"Payment enabled but not implemented - granting trial to {telegram_id}")
        
        # MVP РЕЖИМ или временный доступ: Сразу даем доступ
        # Подписка уже создана с правильным статусом в get_or_create_subscription()
        logger.info(
            f"User {telegram_id} granted access: "
            f"payment_enabled={settings.payment_enabled}, "
            f"subscription_status={subscription.status}"
        )
        
        # ============================================
        
        # Временно: сохраняем обратную совместимость с payment_status
        await send_google_sheet(message, session, user, data['name'])
        
        # Очищаем состояние
        await state.clear()
        
        logger.info(f"User registered successfully: telegram_id={telegram_id}, name={data['name']}")
        
    except Exception as e:
        logger.error(f"Error during registration: {e}", exc_info=True)
        await state.clear()
        await message.answer(
            Messages.error_general(),
            parse_mode="HTML",
            reply_markup=remove_keyboard()
        )


async def send_google_sheet(message: Message, session: AsyncSession, user, name: str):
    """
    Отправка ссылки на Google-таблицу пользователю.
    
    Args:
        message: Сообщение пользователя
        session: Сессия БД
        user: Объект пользователя
        name: Имя пользователя
    """
    # Обновляем статус оплаты (в MVP сразу completed)
    await update_user_payment_status(session, user, 'completed')
    
    # Отмечаем что таблица отправлена
    await mark_google_sheet_sent(session, user)
    
    # Отправляем сообщение об успешной регистрации
    await message.answer(
        Messages.registration_complete(name),
        reply_markup=remove_keyboard(),
        parse_mode="HTML"
    )
    
    # Показываем главное меню
    await message.answer(
        "👇 Выберите действие:",
        reply_markup=get_main_menu_keyboard()
    )
