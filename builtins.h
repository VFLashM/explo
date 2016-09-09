#include <stdio.h> // printf
#include <signal.h>

typedef int Int;
typedef int Bool;
typedef int Unit;
#define false 0
#define true 1
#define unit 0

Bool and(Bool a, Bool b) { return a && b; }
Bool or(Bool a, Bool b) { return a || b; }
Bool xor(Bool a, Bool b) { return a != b; }
Bool not(Bool a) { return !a; }
Bool beq(Bool a, Bool b) { return a == b; }
Bool bneq(Bool a, Bool b) { return a != b; }

Int add(Int a, Int b) { return a + b; }
Int sub(Int a, Int b) { return a - b; }
Int mul(Int a, Int b) { return a * b; }
Int div(Int a, Int b) { return a / b; }
Int mod(Int a, Int b) { return a % b; }
Bool ieq(Int a, Int b) { return a == b; }
Bool ineq(Int a, Int b) { return a != b; }

Bool gt(Int a, Int b) { return a > b; }
Bool geq(Int a, Int b) { return a >= b; }
Bool lt(Int a, Int b) { return a < b; }
Bool leq(Int a, Int b) { return a <= b; }

void iprint(Int a) { printf("%d\n", a); }
void bprint(Bool a) { printf("%d\n", a); }
void abort() {
    fprintf(stderr, "abort");
#ifdef _WIN32
    void exit(int const);
    exit(-SIGABRT);
#else
    raise(SIGABRT);
#endif
}
