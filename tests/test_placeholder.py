import unittest
import re
from main_window import PlaceholderEngine


class TestPlaceholderEngine(unittest.TestCase):
    def test_default_happy_today(self):
        eng = PlaceholderEngine()
        eng.register_handler("Hoje", lambda: "01/01/2000")
        self.assertIn("01/01/2000", eng.process("Hoje: $Hoje$"))

    def test_agora_with_format(self):
        eng = PlaceholderEngine()
        out = eng.process("Hora: $Agora[%H:%M]$")
        # Should match HH:MM
        self.assertRegex(out, r"Hora: \d{2}:\d{2}")

    def test_custom_handler(self):
        eng = PlaceholderEngine()
        eng.register_handler("Nome", lambda: "Alice")
        self.assertEqual(eng.process("Olá $Nome$!"), "Olá Alice!")

    def test_default_value_when_missing_handler(self):
        eng = PlaceholderEngine()
        self.assertEqual(eng.process("Hi $Missing|Default$"), "Hi Default")

    def test_handler_returns_empty_then_default(self):
        eng = PlaceholderEngine()
        eng.register_handler("Maybe", lambda: "")
        self.assertEqual(eng.process("Value: $Maybe|Fallback$"), "Value: Fallback")

    def test_handler_with_args(self):
        eng = PlaceholderEngine()

        def echo(text, times):
            # times will be passed as string; return combined representation
            return f"{text}:{times}"

        eng.register_handler("Echo", echo)
        self.assertEqual(eng.process("X $Echo(Hello,3)$"), "X Hello:3")

    def test_handler_exception_fallback_to_default(self):
        eng = PlaceholderEngine()

        def boom():
            raise RuntimeError("boom")

        eng.register_handler("Boom", boom)
        self.assertEqual(eng.process("Test $Boom|DEF$"), "Test DEF")

    def test_non_string_handler_return_converted(self):
        eng = PlaceholderEngine()
        eng.register_handler("Num", lambda: 42)
        self.assertEqual(eng.process("Num is $Num$"), "Num is 42")

    def test_pipe_in_default_kept(self):
        eng = PlaceholderEngine()
        self.assertEqual(eng.process("Keep $Missing|A|B$"), "Keep A|B")

    def test_handler_returns_none_then_default(self):
        eng = PlaceholderEngine()
        eng.register_handler("N", lambda: None)
        self.assertEqual(eng.process("Val $N|D$"), "Val D")

    def test_quoted_args_with_commas(self):
        eng = PlaceholderEngine()

        def joiner(a, b):
            return f"{a}|{b}"

        eng.register_handler("Join", joiner)
        # Provide a quoted argument that contains a comma
        out = eng.process('X $Join("João, Silva",ABC)$')
        self.assertEqual(out, "X João, Silva|ABC")

    def test_numeric_arg_conversion(self):
        eng = PlaceholderEngine()

        def sum_handler(a, b):
            # expects numeric args
            return a + b

        eng.register_handler("Sum", sum_handler)
        # numeric args should be converted to ints
        self.assertEqual(eng.process("Result: $Sum(2,3)$"), "Result: 5")


if __name__ == "__main__":
    unittest.main()
