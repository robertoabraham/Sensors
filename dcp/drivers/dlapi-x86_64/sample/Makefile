CC = g++

CXXFLAGS = -g -Wall
LIBS = -ldlapi 

TARGET = main

all: $(TARGET)

$(TARGET): $(TARGET).cpp
	$(CC) $(CXXFLAGS) -o $(TARGET) $(TARGET).cpp $(LIBS)

clean:
	$(RM) $(TARGET)
