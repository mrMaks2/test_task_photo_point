import logging
from django.test import TestCase
from logging_utils import get_log_level, setup_logger

class LoggingUtilsTest(TestCase):
    def test_get_log_level_development(self):
        """Тест уровня логирования для development"""
        level = get_log_level('development')
        self.assertEqual(level, logging.INFO)

    def test_get_log_level_production(self):
        """Тест уровня логирования для production"""
        level = get_log_level('production')
        self.assertEqual(level, logging.WARNING)

    def test_get_log_level_testing(self):
        """Тест уровня логирования для testing"""
        level = get_log_level('testing')
        self.assertEqual(level, logging.DEBUG)

    def test_get_log_level_unknown(self):
        """Тест уровня логирования для неизвестного окружения"""
        level = get_log_level('unknown')
        self.assertEqual(level, logging.WARNING)

    def test_setup_logger(self):
        """Тест настройки логгера"""
        logger = setup_logger('test_logger')
        
        self.assertEqual(logger.level, logging.INFO)  # development по умолчанию
        self.assertEqual(len(logger.handlers), 1)
        self.assertIsInstance(logger.handlers[0], logging.StreamHandler)