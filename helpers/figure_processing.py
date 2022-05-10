import math


def truncate(number, digits) -> float:
    stepper = 10.0 ** digits
    return math.trunc(stepper * number) / stepper


if __name__ == "__main__":
    print("Truncate result: ", truncate(0.2191780821917808219178082192, 5))
