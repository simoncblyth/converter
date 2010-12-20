from converter.tokenizer import Tokenizer

t = Tokenizer("hello ~ world & yeah & ooodles & doodles ")
ts = t.tokenize()

for x in ts:
    print x

