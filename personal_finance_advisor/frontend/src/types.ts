export type FinancialProfile = {
  name: string;
  age?: number;
  income?: number;
  currency: string;
  financial_goals: string[];
  risk_tolerance: string;
  monthly_expenses_estimate?: number;
  savings_balance?: number;
  debt_balance?: number;
};

export type Transaction = {
  id?: number;
  date: string;
  amount: number;
  category: string;
  merchant?: string;
  description?: string;
  transaction_type: string;
  payment_method?: string;
  is_recurring?: boolean;
  notes?: string;
};

export type Budget = {
  id?: number;
  category: string;
  monthly_limit: number;
  currency: string;
};

export type FinancialGoal = {
  id?: number;
  name: string;
  target_amount: number;
  current_amount: number;
  target_date?: string;
  priority: string;
  description?: string;
};

export type FinanceMessage = {
  role: "user" | "assistant";
  content: string;
};
