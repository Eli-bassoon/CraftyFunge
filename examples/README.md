# Example Programs

These are already in the world download, and can be loaded from a structure block using `craftyfunge:examples/<NAME>`. This directory is provided for using the external interpreter.

| Name              | Notes                                                        |
| ----------------- | ------------------------------------------------------------ |
| `brainfuck.bf`    | A brainfuck interpreter. Horribly slow and inefficient, with a maximum program length of 40<sup>3</sup>=64,000. Input to brainfuck must be separated by `!`. I highly recommend executing this with the external interpreter rather than in Minecraft. If you are pasting in a program to STDIN rather than an external file, you must include an exclamation point as the last character of the program before any input. |
| `cat.nbt`         | A cat program.                                               |
| `digitalroot.nbt` | Calculates the [digital root](https://en.wikipedia.org/wiki/Digital_root) of the input, found by iteratively adding the digits of the previous result until a single-digit number is reached. |
| `disan.nbt`       | Implements the [Disan count](https://esolangs.org/wiki/Disan_Count) algorithm, which prints all the even numbers up to the input. |
| `factorial.nbt`   | Calculates the factorial of the input.                       |
| `gcd.nbt`         | Calculates the greatest common denominator of the first two numbers of the input, using the Euclidean GCD algorithm. |
| `helloworld1.nbt` | A hello world program.                                       |
| `helloworld2.nbt` | Another hello world program, using string literal input mode. |
| `primesieve.nbt`  | Uses the sieve of Eratosthenes to print the primes up to 100. |

