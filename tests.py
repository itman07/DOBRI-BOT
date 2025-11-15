import pytest
import logging
from unittest.mock import AsyncMock, patch
import sys
import os

# Добавляем путь к модулю
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from maxbot import Bot, Dispatcher, Router, configure_logging
from maxbot._types import Message, User, Chat, Update, CallbackQuery
from maxbot.filters import Command, CallbackQueryFilter

class TestMaxBotFixed:
    @pytest.fixture
    def bot(self):
        """Fixture для создания бота"""
        return Bot("test_token")
    
    @pytest.fixture
    def dispatcher(self, bot):
        """Fixture для создания диспетчера"""
        return Dispatcher(bot)
    
    @pytest.mark.asyncio
    async def test_bot_initialization(self):
        """Тест инициализации бота"""
        bot = Bot("test_token")
        assert bot.token == "test_token"
        assert bot.base_url == "https://platform-api.max.ru"
    
    @pytest.mark.asyncio
    async def test_bot_setup_and_close(self, bot):
        """Тест настройки и закрытия бота"""
        await bot.setup()
        assert bot.session is not None
        await bot.close()
    
    @pytest.mark.asyncio
    async def test_get_me(self, bot):
        """Тест получения информации о боте"""
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.json.return_value = {
                "user_id": 123,
                "first_name": "TestBot",
                "is_bot": True
            }
            mock_get.return_value.__aenter__.return_value = mock_response

            await bot.setup()
            result = await bot.get_me()

            assert result["user_id"] == 123
            assert result["first_name"] == "TestBot"
            await bot.close()
    
    @pytest.mark.asyncio
    async def test_send_message(self, bot):
        """Тест отправки сообщения"""
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.json.return_value = {
                "message": {"mid": "test_message_id"}
            }
            mock_post.return_value.__aenter__.return_value = mock_response

            await bot.setup()
            result = await bot.send_message(123, "Hello World")

            assert result["message"]["mid"] == "test_message_id"
            await bot.close()
    
    @pytest.mark.asyncio
    async def test_command_filter(self):
        """Тест фильтра команд"""
        command_filter = Command("start")
        
        # Test matching command
        update = Update(
            update_id=1,
            update_type="message_created",
            timestamp=123456789,
            message=Message(
                message_id="1",
                chat=Chat(chat_id=1, type="chat", status="active"),
                from_user=User(
                    user_id=1, 
                    first_name="Test",
                    last_name="User",
                    username="testuser",
                    is_bot=False,
                    last_activity_time=123456789
                ),
                text="/start"
            )
        )
        
        result = await command_filter(update)
        assert result
        
        # Test non-matching command
        update.message.text = "/help"
        result = await command_filter(update)
        assert not result
        
        # Test non-command message
        update.message.text = "Hello"
        result = await command_filter(update)
        assert not result
    
    @pytest.mark.asyncio
    async def test_message_handler(self, dispatcher):
        """Тест обработчика сообщений"""
        handler_called = False
        
        @dispatcher.message_handler(Command("start"))
        async def start_handler(update, bot):
            nonlocal handler_called
            handler_called = True
        
        update = Update(
            update_id=1,
            update_type="message_created", 
            timestamp=123456789,
            message=Message(
                message_id="1",
                chat=Chat(chat_id=1, type="chat", status="active"),
                from_user=User(
                    user_id=1,
                    first_name="Test",
                    last_name="User", 
                    username="testuser",
                    is_bot=False,
                    last_activity_time=123456789
                ),
                text="/start"
            )
        )
        
        await dispatcher.process_update(update)
        assert handler_called
    
    @pytest.mark.asyncio 
    async def test_callback_query_handler(self, dispatcher):
        """Тест обработчика callback запросов"""
        handler_called = False
        
        @dispatcher.callback_query_handler(CallbackQueryFilter("test_data"))
        async def callback_handler(update, bot):
            nonlocal handler_called
            handler_called = True
        
        update = Update(
            update_id=1,
            update_type="message_callback",
            timestamp=123456789,
            callback_query=CallbackQuery(
                callback_id="1",
                from_user=User(
                    user_id=1,
                    first_name="Test",
                    last_name="User",
                    username="testuser", 
                    is_bot=False,
                    last_activity_time=123456789
                ),
                payload="test_data"
            )
        )
        
        await dispatcher.process_update(update)
        assert handler_called
    
    @pytest.mark.asyncio
    async def test_router_integration(self, dispatcher):
        """Тест интеграции роутера"""
        router = Router("test_router")
        handler_called = False
        
        @router.message_handler(Command("help"))
        async def help_handler(update, bot):
            nonlocal handler_called
            handler_called = True
        
        router.include_in_dispatcher(dispatcher)
        
        update = Update(
            update_id=1,
            update_type="message_created",
            timestamp=123456789,
            message=Message(
                message_id="1",
                chat=Chat(chat_id=1, type="chat", status="active"),
                from_user=User(
                    user_id=1,
                    first_name="Test",
                    last_name="User",
                    username="testuser",
                    is_bot=False,
                    last_activity_time=123456789
                ),
                text="/help"
            )
        )
        
        await dispatcher.process_update(update)
        assert handler_called

class TestLoggingFixed:
    """Тесты для логирования"""
    
    def setup_method(self):
        """Настройка перед каждым тестом"""
        configure_logging(level=logging.DEBUG)
    
    @pytest.mark.asyncio
    async def test_bot_logging(self, caplog):
        """Тест логирования в боте"""
        caplog.set_level(logging.DEBUG)
        
        bot = Bot("test_token")
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.json.return_value = {
                "user_id": 123,
                "first_name": "TestBot",
                "is_bot": True
            }
            mock_get.return_value.__aenter__.return_value = mock_response
            
            await bot.setup()
            await bot.get_me()
            await bot.close()
        
        # Проверяем что логи были записаны
        log_messages = [record.message for record in caplog.records]
        assert any("Setting up aiohttp session" in message for message in log_messages)
        assert any("Bot session initialized" in message for message in log_messages)
    
    @pytest.mark.asyncio
    async def test_dispatcher_logging(self, caplog):
        """Тест логирования в диспетчере"""
        caplog.set_level(logging.DEBUG)
        
        bot = Bot("test_token")
        dispatcher = Dispatcher(bot)
        
        @dispatcher.message_handler(Command("test"))
        async def test_handler(update, bot):
            pass
        
        update = Update(
            update_id=1,
            update_type="message_created",
            timestamp=123456789,
            message=Message(
                message_id="1",
                chat=Chat(chat_id=1, type="chat", status="active"),
                from_user=User(
                    user_id=1,
                    first_name="Test",
                    last_name="User",
                    username="testuser",
                    is_bot=False,
                    last_activity_time=123456789
                ),
                text="/test"
            )
        )
        
        await dispatcher.process_update(update)
        
        log_messages = [record.message for record in caplog.records]
        assert any("Processing message update" in message for message in log_messages)
        assert any("Executing handler: test_handler" in message for message in log_messages)
    
    def test_logging_configuration(self):
        """Тест конфигурации логирования"""
        # Test different levels
        configure_logging(level=logging.DEBUG)
        logger = logging.getLogger("maxbot")
        assert logger.level == logging.DEBUG
        
        configure_logging(level=logging.WARNING)
        logger = logging.getLogger("maxbot")
        assert logger.level == logging.WARNING

@pytest.mark.asyncio
async def test_error_handling_in_dispatcher():
    """Тест обработки ошибок в диспетчере"""
    bot = Bot("test_token")
    dispatcher = Dispatcher(bot)
    
    error_occurred = False
    
    @dispatcher.message_handler(Command("error"))
    async def error_handler(update, bot):
        nonlocal error_occurred
        error_occurred = True
        raise ValueError("Test error")
    
    update = Update(
        update_id=1,
        update_type="message_created",
        timestamp=123456789,
        message=Message(
            message_id="1",
            chat=Chat(chat_id=1, type="chat", status="active"),
            from_user=User(
                user_id=1,
                first_name="Test",
                last_name="User",
                username="testuser",
                is_bot=False,
                last_activity_time=123456789
            ),
            text="/error"
        )
    )
    
    # Обработка не должна падать с исключением
    await dispatcher.process_update(update)
    assert error_occurred

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])