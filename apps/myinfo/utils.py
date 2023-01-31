def number_to_ordinal(num: int):
    nth = {1: "first", 2: "second", 3: "third", 4: "fourth", 5: "fifth"}
    return nth[num]