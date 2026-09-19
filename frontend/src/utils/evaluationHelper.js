export function generateEvaluationData(extractedText = '', fileName = '') {
  const combined = (extractedText + ' ' + fileName).toLowerCase();
  
  // Check if it's a Python exam or student answer sheet
  if (combined.includes('python') || combined.includes('variable') || combined.includes('if-else') || combined.includes('riya')) {
    let studentAns = extractedText;
    if (!studentAns || studentAns.length < 30) {
      studentAns = `Answer 1: A variable is a name that refers to a value stored during program execution. In Python, a variable is created by assigning a value to a name, and an explicit data-type declaration is not required. For example, name = "Riya" and age = 20. Python automatically determines the type of the assigned value, and the value of a variable can be changed during execution.\n\nAnswer 2: An if-else statement is a decision-making statement used to execute different blocks of code depending on whether a condition is true or false. Python uses indentation to define the blocks. For example, age = 18; if age >= 18: print("Adult") else: print("Minor").\n\nAnswer 3: A loop is a statement used to store different values in a variable. Python uses if-else statements and variables to perform looping. For example, if i < 3: print(i) is a loop that repeatedly prints values.`;
    } else {
      // Format answers cleanly if it contains Answer 1, 2, 3
      studentAns = studentAns
        .replace(/(Answer\s*1:?)/gi, '\n[Answer 1]: ')
        .replace(/(Answer\s*2:?)/gi, '\n\n[Answer 2]: ')
        .replace(/(Answer\s*3:?)/gi, '\n\n[Answer 3]: ')
        .trim();
    }

    return {
      sheetId: 'SHEET-PYTHON-402',
      studentRoll: 'CS21B042',
      subject: 'Python Programming',
      score: 7.5,
      maxScore: 10,
      aiConfidence: 92,
      reviewStatus: 'NEEDS_REVIEW',
      studentAnswer: studentAns,
      expectedAnswer: `Q1 (Variables - 3.5 Marks): A variable is a named reference to an object stored in memory. Python uses dynamic typing without explicit type declarations.\n\nQ2 (If-Else - 3.5 Marks): An if-else statement is a control flow structure that branches execution based on boolean conditions. Code blocks are defined strictly using indentation.\n\nQ3 (Loops - 3.0 Marks): Control structures ('for' and 'while' loops) used to repeatedly execute a block of statements over an iterable sequence or until a terminating condition is met.`,
      llmRationale: `• Q1 (3.5/3.5): Fully correct. Accurate explanation of dynamic typing and variable assignment with valid code examples.\n• Q2 (3.5/3.5): Fully correct. Correctly describes conditional execution and Python indentation syntax.\n• Q3 (0.5/3.0): Conceptual error. The student confused loops with conditional if-statements and variables instead of describing 'for' or 'while' iteration constructs. Deducted 2.5 marks.\n\nTotal Score: 7.5 / 10.`,
      missingConcepts: [
        "for loop syntax and iterable sequence traversal",
        "while loop condition evaluation and termination",
        "Distinction between iterative loop structures and conditional branching statements"
      ]
    };
  }

  // Default Math / Quadratic Factorization demo
  return {
    sheetId: 'SHEET-MATH-402',
    studentRoll: 'MATH-102',
    subject: 'Mathematics - Algebra',
    score: 10,
    maxScore: 10,
    aiConfidence: 96,
    reviewStatus: 'NEEDS_REVIEW',
    studentAnswer: `2x² - x - 6 = 0\n2x² - 4x + 3x - 6 = 0\n2x(x - 2) + 3(x - 2) = 0\n(2x + 3)(x - 2) = 0\nx = -3/2, x = 2`,
    expectedAnswer: `To solve 2x² - x - 6 = 0: Split the middle term to get 2x² - 4x + 3x - 6 = 0. Factorize: 2x(x - 2) + 3(x - 2) = 0, giving (2x + 3)(x - 2) = 0. Roots: x = -3/2, x = 2.`,
    llmRationale: `The student correctly used the middle-term splitting method for quadratic factorization. All algebraic steps are clear and logically sound, leading to the correct roots. Awarding full marks.`,
    missingConcepts: []
  };
}
