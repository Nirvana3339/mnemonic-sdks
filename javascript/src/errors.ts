/**
 * Mnemonic SDK Error Classes
 */

export class MnemonicError extends Error {
  statusCode?: number;
  response?: any;

  constructor(message: string, statusCode?: number, response?: any) {
    super(message);
    this.name = 'MnemonicError';
    this.statusCode = statusCode;
    this.response = response;
    Object.setPrototypeOf(this, MnemonicError.prototype);
  }
}

export class AuthError extends MnemonicError {
  constructor(message: string = 'Invalid API key') {
    super(message, 401);
    this.name = 'AuthError';
    Object.setPrototypeOf(this, AuthError.prototype);
  }
}

export class NotFoundError extends MnemonicError {
  constructor(message: string = 'Resource not found') {
    super(message, 404);
    this.name = 'NotFoundError';
    Object.setPrototypeOf(this, NotFoundError.prototype);
  }
}

export class RateLimitError extends MnemonicError {
  constructor(message: string = 'Rate limit exceeded') {
    super(message, 429);
    this.name = 'RateLimitError';
    Object.setPrototypeOf(this, RateLimitError.prototype);
  }
}

export class ValidationError extends MnemonicError {
  constructor(message: string = 'Validation failed') {
    super(message, 422);
    this.name = 'ValidationError';
    Object.setPrototypeOf(this, ValidationError.prototype);
  }
}
