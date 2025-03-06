#include <stdio.h>
#include <stdlib.h>
typedef struct Hello{
    int num;
    void (*sayHello) (const char* name);
    int (*getNum)(struct Hello* this);
} Hello;
void sayHello(const char* name);
Hello* createHello();
int getNum(Hello* this);

int main(){
    printf("Hello, World!\n");
    printf("Input your name: ");
    char* name;
    name = (char*)malloc(sizeof(char)*100);
    scanf("%s", name);
    Hello* hello = createHello();
    hello->sayHello(name);
    printf("Num: %d\n", hello->getNum(hello));
    return 0;
}
int getNum(Hello* this){
    return this->num;
}


void sayHello(const char* name){
    printf("Hello, %s!\n", name);
}

Hello* createHello(){
    Hello* hello = (Hello*)malloc(sizeof(Hello));
    hello->sayHello = sayHello;
    hello->num = 10;
    hello->getNum = getNum;
    return hello;
}

