CXX = g++
CXXFLAGS = -g -Wall -std=c++1z
LIBS = -ldlapi -lm -ldl -ltinyxml2 -lboost_system -lboost_filesystem -lcfitsio -lfmt
SOURCES = $(wildcard *.cpp)
OBJS := $(SOURCES:.cpp=.o)
TARGET = dfcore

all: $(TARGET)

$(TARGET): $(OBJS)
	$(CXX) $(LDFLAGS) $(CXXFLAGS) $^ -o $@ $(LIBS)

clean:
	rm -f $(OBJS)

install: $(TARGET)
	cp $(TARGET) /usr/local/bin

