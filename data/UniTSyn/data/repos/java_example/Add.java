
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

/**
 * Add
 */
public class Add {
    public static void main(String[] args) {
        int a = 10;
        int b = 20;
        int c = add(a, b);
        System.out.println("Sum of a and b is: " + c);
    }

    public static int add(int a, int b) {
        return a + b;
    }

    @Deprecated
    public static int sub(int a, int b) {
        return a - b;
    }


    @Test
    public void testAdd() {
        Assertions.assertEquals(30, add(10, 20));
    }

    public void testSub() {
        Assertions.assertEquals(10, sub(20, 10));
    }
}