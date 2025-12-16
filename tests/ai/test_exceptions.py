"""
Тесты для модуля exceptions.py
"""

import pytest
from ai.exceptions import (
    AIPlayerError,
    InvalidStateError,
    ConfigurationError,
    PredictionError,
    LearningError,
    DataError,
)


class TestExceptions:
    """Тесты для исключений."""

    def test_ai_player_error(self):
        """Тест базового исключения AIPlayerError."""
        error = AIPlayerError("Test error")
        assert str(error) == "Test error"
        assert isinstance(error, Exception)

    def test_invalid_state_error(self):
        """Тест исключения InvalidStateError."""
        error = InvalidStateError("Invalid state")
        assert str(error) == "Invalid state"
        assert isinstance(error, AIPlayerError)

    def test_configuration_error(self):
        """Тест исключения ConfigurationError."""
        error = ConfigurationError("Config error")
        assert str(error) == "Config error"
        assert isinstance(error, AIPlayerError)

    def test_prediction_error(self):
        """Тест исключения PredictionError."""
        error = PredictionError("Prediction failed")
        assert str(error) == "Prediction failed"
        assert isinstance(error, AIPlayerError)

    def test_learning_error(self):
        """Тест исключения LearningError."""
        error = LearningError("Learning failed")
        assert str(error) == "Learning failed"
        assert isinstance(error, AIPlayerError)

    def test_data_error(self):
        """Тест исключения DataError."""
        error = DataError("Data error")
        assert str(error) == "Data error"
        assert isinstance(error, AIPlayerError)

    def test_exception_hierarchy(self):
        """Тест иерархии исключений."""
        assert issubclass(InvalidStateError, AIPlayerError)
        assert issubclass(ConfigurationError, AIPlayerError)
        assert issubclass(PredictionError, AIPlayerError)
        assert issubclass(LearningError, AIPlayerError)
        assert issubclass(DataError, AIPlayerError)
        assert issubclass(AIPlayerError, Exception)
