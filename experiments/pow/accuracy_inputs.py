"""Deterministic random, exceptional, and reduction-boundary double inputs."""
import random, struct, math, pathlib
p = pathlib.Path(__file__).resolve().parent
rng = random.Random(20261029)
rows = []
def emit(domain, x, y): rows.append((domain, x, y))
def bits(x): return struct.unpack('<Q',struct.pack('<d',x))[0]
def value(x): return struct.unpack('<d',struct.pack('<Q',x & ((1<<64)-1)))[0]
for i in range(20000):
    emit('positive',0.5+1.5*rng.random(),-8+16*rng.random())
    emit('near_one',1+(rng.random()-.5)*2e-8,(rng.random()-.5)*2e10)
    emit('negative_integer',-(0.5+1.5*rng.random()),float(rng.randrange(-1024,1025)))
    emit('subnormal',value(rng.randrange(1,1<<52)),rng.uniform(-1.5,1.5))
    emit('range_edge',2+(rng.random()-.5)*1e-12,rng.choice([1024.,-1075.])+(rng.random()-.5)*1e-9)
    emit('random_bits',value(rng.getrandbits(64)),value(rng.getrandbits(64)))
    x=value(rng.randrange(1,0x7ff0000000000000))
    emit('log_uniform',x,rng.uniform(-1100,1100)/max(abs(math.log2(x)),1e-9))
for i in range(129):
    center=0x3fe6955500000000+(i<<45)
    for step in range(-2,3):
        for y in [-1000.1,-31.,-.5,0.5,3.,31.5,1000.1]:emit('table_boundary',value(center+step),y)
for i in range(-128,129):
    x=value(0x3ff0000000000000+i)
    for y in [2**n for n in range(20,65,4)]:
        for sign in [-1,1]:emit('adversarial_one',x,sign*y)
sp=[0.,-0.,1.,-1.,2.,-2.,.5,-.5,math.inf,-math.inf,math.nan,value(0x7ff0000000000001),value(1),-value(1),value(0x0010000000000000),value(0x7fefffffffffffff),2**53,-2**53,3.,-3.]
for x in sp:
    for y in sp:emit('special',x,y)
(p/'results/artifacts/inputs.bin').write_bytes(b''.join(struct.pack('<dd',x,y) for _,x,y in rows))
(p/'results/raw/accuracy-domains.txt').write_text('\n'.join(d for d,_,_ in rows)+'\n')
print(f'{len(rows)} cases, seed 20261029')
