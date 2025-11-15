# Frontend AI Chat Integration Guide

## Обзор

Полное руководство по интеграции AI чата с RAG в React/TypeScript приложение. Включает TypeScript интерфейсы, компоненты drag-and-drop, markdown рендеринг, управление состоянием и обработку ошибок.

## 🎯 Концепция: Floating Chat Widget

**UI/UX Спецификация:**
- ✅ Фиксированный круглый виджет в правом нижнем углу (`position: fixed; bottom: 20px; right: 20px`)
- ✅ При клике открывается чат-окно (размер: 400x600px, можно сделать draggable)
- ✅ Выбор документов из списка существующих (DocumentService)
- ✅ Будущее: drag-and-drop загрузка новых файлов прямо в чат
- ✅ Автоматическое RAG преобразование PDF при активации функции `view_pdf`
- ✅ Контекст документов автоматически прикрепляется к чату через knowledge base

**Workflow:**
1. Пользователь кликает на круглый виджет → открывается чат
2. В чате можно выбрать документы из существующих (список DocumentService где `is_public=true` или `author_id=current_user`)
3. При выборе документа:
   - Если у документа `view_pdf=true` → RAG данные уже готовы (автоматически обработаны при загрузке)
   - Если `view_pdf=false` → показать уведомление "Включите функцию просмотра PDF для использования в чате"
4. Выбранные документы добавляются в knowledge base чата
5. При отправке сообщения → backend автоматически использует RAG контекст из документов

## TypeScript Interface Definitions

### Базовые интерфейсы

```typescript
// src/types/chat.ts

/**
 * Сообщение в чате (пользователь или AI)
 */
export interface ChatMessage {
  /** Роль отправителя: 'user' или 'assistant' */
  role: 'user' | 'assistant';

  /** Текстовое содержимое сообщения (поддерживает Markdown) */
  content: string;

  /** Метаданные сообщения */
  metadata: {
    /** Количество токенов использованных для генерации (только для assistant) */
    tokens_used?: number;

    /** Количество RAG чанков использованных из документов (только для assistant) */
    rag_chunks_used?: number;

    /** Ключ модели использованной для ответа (только для assistant) */
    model_key?: string;
  };

  /** ISO 8601 timestamp отправки */
  timestamp: string;
}

/**
 * Настройки модели для чата
 */
export interface ChatModelSettings {
  /** Креативность ответов: 0.0 (точно) - 2.0 (креативно) */
  temperature: number;

  /** Максимум токенов в ответе модели */
  max_tokens: number;

  /** Системный промпт (опционально) */
  system_prompt?: string | null;
}

/**
 * Метаданные использования чата
 */
export interface ChatMetadata {
  /** Общее количество токенов использованных в чате */
  tokens_used: number;

  /** Количество сообщений в чате */
  messages_count: number;

  /** Примерная стоимость в USD (для платных моделей) */
  estimated_cost: number;

  /** Количество RAG запросов выполненных */
  rag_queries_count: number;
}

/**
 * Краткая информация о чате (для списка)
 */
export interface ChatListItem {
  /** UUID чата в БД */
  id: string;

  /** Читаемый идентификатор (например, "chat-abc123xyz") */
  chat_id: string;

  /** Название чата */
  title: string;

  /** Ключ текущей модели (qwen_coder, kimi_dev, и т.д.) */
  model_key: string;

  /** Имя модели (computed field от backend) */
  model_name: string;

  /** Количество сообщений в чате */
  messages_count: number;

  /** UUID workspace (null для персональных чатов) */
  workspace_id: string | null;

  /** ISO 8601 timestamp создания */
  created_at: string;

  /** ISO 8601 timestamp последнего обновления */
  updated_at: string;
}

/**
 * Полная детальная информация о чате
 */
export interface ChatDetail {
  /** UUID чата в БД */
  id: string;

  /** Читаемый идентификатор */
  chat_id: string;

  /** Название чата */
  title: string;

  /** Ключ текущей модели */
  model_key: string;

  /** Имя модели (computed field) */
  model_name: string;

  /** UUID владельца чата */
  user_id: string;

  /** UUID workspace (null для персональных) */
  workspace_id: string | null;

  /** Список UUID документов добавленных в RAG контекст */
  document_service_ids: string[];

  /** История сообщений */
  messages: ChatMessage[];

  /** Настройки текущей модели */
  model_settings: ChatModelSettings;

  /** Метаданные использования */
  metadata: ChatMetadata;

  /** Активен ли чат (false = soft deleted) */
  is_active: boolean;

  /** ISO 8601 timestamp создания */
  created_at: string;

  /** ISO 8601 timestamp последнего обновления */
  updated_at: string;
}

/**
 * Информация о доступной AI модели
 */
export interface ModelInfo {
  /** Ключ модели для API запросов */
  key: string;

  /** OpenRouter ID модели */
  id: string;

  /** Человекочитаемое имя */
  name: string;

  /** Описание модели */
  description: string;

  /** Специализация (код, исследования, и т.д.) */
  specialization: string;

  /** Максимальный context window в токенах */
  context_window: number;

  /** Дефолтная temperature */
  default_temperature: number;

  /** Дефолтный max_tokens */
  default_max_tokens: number;
}

/**
 * Ответ от AI assistant
 */
export interface MessageResponse {
  role: 'assistant';
  content: string;
  metadata: {
    tokens_used: number;
    rag_chunks_used: number;
    model_key: string;
  };
  timestamp: string;
}

/**
 * Стандартный формат API ответов
 */
export interface APIResponse<T> {
  success: boolean;
  message: string;
  data: T | null;
}
```

## API Client Setup

### Axios Instance с Authentication

```typescript
// src/api/client.ts

import axios, { AxiosError, AxiosInstance } from 'axios';

/**
 * Axios instance с автоматическим добавлением JWT токена
 */
export const apiClient: AxiosInstance = axios.create({
  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1',
  timeout: 30000, // 30 секунд (OpenRouter может быть медленным)
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * Request interceptor: добавляем JWT токен из localStorage
 */
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

/**
 * Response interceptor: обработка 401 (refresh token или logout)
 */
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<APIResponse<null>>) => {
    if (error.response?.status === 401) {
      // Попробовать refresh token
      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        try {
          const response = await axios.post(
            `${process.env.REACT_APP_API_URL}/auth/refresh`,
            { refresh_token: refreshToken }
          );
          const { access_token, refresh_token: new_refresh } = response.data.data;

          localStorage.setItem('access_token', access_token);
          if (new_refresh) {
            localStorage.setItem('refresh_token', new_refresh);
          }

          // Повторить оригинальный запрос
          error.config!.headers.Authorization = `Bearer ${access_token}`;
          return apiClient.request(error.config!);
        } catch (refreshError) {
          // Refresh failed → logout
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          window.location.href = '/login';
        }
      } else {
        // Нет refresh token → logout
        localStorage.removeItem('access_token');
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

/**
 * Helper для обработки ошибок API
 */
export const getErrorMessage = (error: unknown): string => {
  if (axios.isAxiosError(error)) {
    const apiError = error as AxiosError<APIResponse<null>>;
    return apiError.response?.data?.message || 'Network error';
  }
  return 'Unknown error';
};
```

## Chat API Service

### API методы для работы с чатами

```typescript
// src/api/chat.service.ts

import { apiClient, getErrorMessage } from './client';
import type {
  ModelInfo,
  ChatListItem,
  ChatDetail,
  MessageResponse,
  APIResponse,
} from '../types/chat';

export class ChatAPI {
  /**
   * Получить список доступных AI моделей
   */
  static async getModels(): Promise<ModelInfo[]> {
    try {
      const response = await apiClient.get<APIResponse<ModelInfo[]>>('/chat/models');
      return response.data.data || [];
    } catch (error) {
      throw new Error(`Failed to load models: ${getErrorMessage(error)}`);
    }
  }

  /**
   * Создать новый чат
   */
  static async createChat(params: {
    model_key: string;
    title: string;
    workspace_id?: string | null;
    document_service_ids?: string[];
    system_prompt?: string | null;
  }): Promise<ChatDetail> {
    try {
      const response = await apiClient.post<APIResponse<ChatDetail>>('/chat', params);
      if (!response.data.data) {
        throw new Error('No chat data in response');
      }
      return response.data.data;
    } catch (error) {
      throw new Error(`Failed to create chat: ${getErrorMessage(error)}`);
    }
  }

  /**
   * Получить список чатов пользователя
   */
  static async listChats(limit: number = 50): Promise<ChatListItem[]> {
    try {
      const response = await apiClient.get<APIResponse<ChatListItem[]>>(
        `/chat?limit=${limit}`
      );
      return response.data.data || [];
    } catch (error) {
      throw new Error(`Failed to load chats: ${getErrorMessage(error)}`);
    }
  }

  /**
   * Получить детали чата с историей сообщений
   */
  static async getChatDetail(chatId: string): Promise<ChatDetail> {
    try {
      const response = await apiClient.get<APIResponse<ChatDetail>>(`/chat/${chatId}`);
      if (!response.data.data) {
        throw new Error('Chat not found');
      }
      return response.data.data;
    } catch (error) {
      throw new Error(`Failed to load chat: ${getErrorMessage(error)}`);
    }
  }

  /**
   * Отправить текстовое сообщение
   */
  static async sendMessage(
    chatId: string,
    content: string
  ): Promise<MessageResponse> {
    try {
      const formData = new FormData();
      formData.append('content', content);

      const response = await apiClient.post<APIResponse<MessageResponse>>(
        `/chat/${chatId}/message`,
        formData,
        {
          headers: { 'Content-Type': 'multipart/form-data' },
        }
      );

      if (!response.data.data) {
        throw new Error('No response from AI');
      }
      return response.data.data;
    } catch (error) {
      throw new Error(`Failed to send message: ${getErrorMessage(error)}`);
    }
  }

  /**
   * Отправить сообщение с файлом (drag-and-drop)
   */
  static async sendMessageWithFile(
    chatId: string,
    content: string,
    file: File,
    onProgress?: (percent: number) => void
  ): Promise<MessageResponse> {
    try {
      const formData = new FormData();
      formData.append('content', content);
      formData.append('file', file);

      const response = await apiClient.post<APIResponse<MessageResponse>>(
        `/chat/${chatId}/message`,
        formData,
        {
          headers: { 'Content-Type': 'multipart/form-data' },
          onUploadProgress: (progressEvent) => {
            if (onProgress && progressEvent.total) {
              const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
              onProgress(percent);
            }
          },
        }
      );

      if (!response.data.data) {
        throw new Error('No response from AI');
      }
      return response.data.data;
    } catch (error) {
      throw new Error(`Failed to send message with file: ${getErrorMessage(error)}`);
    }
  }

  /**
   * Переключить модель в чате (сохраняет историю)
   */
  static async switchModel(chatId: string, modelKey: string): Promise<ChatDetail> {
    try {
      const response = await apiClient.patch<APIResponse<ChatDetail>>(
        `/chat/${chatId}/model`,
        { model_key: modelKey }
      );

      if (!response.data.data) {
        throw new Error('Failed to switch model');
      }
      return response.data.data;
    } catch (error) {
      throw new Error(`Failed to switch model: ${getErrorMessage(error)}`);
    }
  }

  /**
   * Добавить документы в чат (для RAG)
   */
  static async addDocuments(
    chatId: string,
    documentServiceIds: string[]
  ): Promise<ChatDetail> {
    try {
      const response = await apiClient.post<APIResponse<ChatDetail>>(
        `/chat/${chatId}/documents`,
        { document_service_ids: documentServiceIds }
      );

      if (!response.data.data) {
        throw new Error('Failed to add documents');
      }
      return response.data.data;
    } catch (error) {
      throw new Error(`Failed to add documents: ${getErrorMessage(error)}`);
    }
  }

  /**
   * Удалить чат (soft delete)
   */
  static async deleteChat(chatId: string): Promise<void> {
    try {
      await apiClient.delete(`/chat/${chatId}`);
    } catch (error) {
      throw new Error(`Failed to delete chat: ${getErrorMessage(error)}`);
    }
  }
}
```

## React Components

### 1. Model Selector Dropdown

```tsx
// src/components/chat/ModelSelector.tsx

import React, { useEffect, useState } from 'react';
import { ChatAPI } from '../../api/chat.service';
import type { ModelInfo } from '../../types/chat';

interface ModelSelectorProps {
  /** Текущий ключ модели */
  currentModel: string;

  /** Callback при переключении модели */
  onSwitch: (modelKey: string) => Promise<void>;

  /** Disabled state */
  disabled?: boolean;
}

export const ModelSelector: React.FC<ModelSelectorProps> = ({
  currentModel,
  onSwitch,
  disabled = false,
}) => {
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [switching, setSwitching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadModels();
  }, []);

  const loadModels = async () => {
    try {
      setLoading(true);
      const data = await ChatAPI.getModels();
      setModels(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load models');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = async (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newModelKey = e.target.value;
    if (newModelKey === currentModel) return;

    try {
      setSwitching(true);
      await onSwitch(newModelKey);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to switch model');
    } finally {
      setSwitching(false);
    }
  };

  if (loading) {
    return <div className="model-selector loading">Loading models...</div>;
  }

  if (error) {
    return (
      <div className="model-selector error">
        {error}
        <button onClick={loadModels}>Retry</button>
      </div>
    );
  }

  return (
    <div className="model-selector">
      <label htmlFor="model-select">AI Model:</label>
      <select
        id="model-select"
        value={currentModel}
        onChange={handleChange}
        disabled={disabled || switching}
        className={switching ? 'switching' : ''}
      >
        {models.map((model) => (
          <option key={model.key} value={model.key} title={model.description}>
            {model.name} - {model.specialization}
            {model.context_window >= 100000 && ' 🚀'}
          </option>
        ))}
      </select>
      {switching && <span className="spinner">Switching...</span>}
    </div>
  );
};
```

### 2. Chat Message List with Markdown

```tsx
// src/components/chat/ChatMessages.tsx

import React, { useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import type { ChatMessage } from '../../types/chat';

interface ChatMessagesProps {
  /** Список сообщений для отображения */
  messages: ChatMessage[];

  /** Флаг загрузки (показывать индикатор AI typing) */
  isLoading?: boolean;
}

export const ChatMessages: React.FC<ChatMessagesProps> = ({
  messages,
  isLoading = false,
}) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll к последнему сообщению
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  return (
    <div className="chat-messages">
      {messages.map((message, index) => (
        <div
          key={index}
          className={`message message-${message.role}`}
          data-role={message.role}
        >
          <div className="message-avatar">
            {message.role === 'user' ? '👤' : '🤖'}
          </div>

          <div className="message-content">
            <ReactMarkdown
              components={{
                // Подсветка синтаксиса для блоков кода
                code({ node, inline, className, children, ...props }) {
                  const match = /language-(\w+)/.exec(className || '');
                  return !inline && match ? (
                    <SyntaxHighlighter
                      style={vscDarkPlus}
                      language={match[1]}
                      PreTag="div"
                      {...props}
                    >
                      {String(children).replace(/\n$/, '')}
                    </SyntaxHighlighter>
                  ) : (
                    <code className={className} {...props}>
                      {children}
                    </code>
                  );
                },
              }}
            >
              {message.content}
            </ReactMarkdown>

            {/* Метаданные для assistant сообщений */}
            {message.role === 'assistant' && (
              <div className="message-metadata">
                {message.metadata.rag_chunks_used > 0 && (
                  <span className="rag-indicator" title="RAG context used">
                    📎 {message.metadata.rag_chunks_used} документа
                  </span>
                )}
                {message.metadata.tokens_used && (
                  <span className="tokens-used" title="Tokens used">
                    🔢 {message.metadata.tokens_used} токенов
                  </span>
                )}
                <span className="timestamp">
                  {new Date(message.timestamp).toLocaleTimeString()}
                </span>
              </div>
            )}
          </div>
        </div>
      ))}

      {/* AI typing indicator */}
      {isLoading && (
        <div className="message message-assistant typing">
          <div className="message-avatar">🤖</div>
          <div className="message-content">
            <div className="typing-indicator">
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
        </div>
      )}

      <div ref={messagesEndRef} />
    </div>
  );
};
```

### 3. Message Input with Drag-and-Drop

```tsx
// src/components/chat/ChatInput.tsx

import React, { useState, useRef } from 'react';

interface ChatInputProps {
  /** Callback отправки сообщения */
  onSendMessage: (content: string, file?: File) => Promise<void>;

  /** Disabled state (во время загрузки) */
  disabled?: boolean;

  /** Placeholder текст */
  placeholder?: string;
}

export const ChatInput: React.FC<ChatInputProps> = ({
  onSendMessage,
  disabled = false,
  placeholder = 'Type your message... (или перетащите файл)',
}) => {
  const [message, setMessage] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<number | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleSend = async () => {
    if (!message.trim() && !file) return;
    if (disabled) return;

    try {
      setUploadProgress(file ? 0 : null);
      await onSendMessage(message, file || undefined);

      // Очистить форму после успешной отправки
      setMessage('');
      setFile(null);
      setUploadProgress(null);
    } catch (error) {
      console.error('Failed to send message:', error);
      setUploadProgress(null);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Drag-and-drop handlers
  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) {
      setFile(droppedFile);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      setFile(selectedFile);
    }
  };

  const removeFile = () => {
    setFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div
      className={`chat-input ${isDragging ? 'dragging' : ''}`}
      onDragEnter={handleDragEnter}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {/* File preview */}
      {file && (
        <div className="file-preview">
          <div className="file-info">
            <span className="file-icon">📎</span>
            <span className="file-name">{file.name}</span>
            <span className="file-size">
              ({(file.size / 1024 / 1024).toFixed(2)} MB)
            </span>
          </div>
          <button
            type="button"
            className="remove-file"
            onClick={removeFile}
            disabled={disabled}
          >
            ✕
          </button>
        </div>
      )}

      {/* Upload progress bar */}
      {uploadProgress !== null && (
        <div className="upload-progress">
          <div
            className="upload-progress-bar"
            style={{ width: `${uploadProgress}%` }}
          />
          <span className="upload-progress-text">{uploadProgress}%</span>
        </div>
      )}

      {/* Input area */}
      <div className="input-area">
        <textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder={placeholder}
          disabled={disabled}
          rows={3}
        />

        <div className="input-actions">
          <input
            ref={fileInputRef}
            type="file"
            onChange={handleFileSelect}
            style={{ display: 'none' }}
            accept=".pdf,.doc,.docx,.txt,.md,.py,.js,.ts,.tsx,.jsx"
          />

          <button
            type="button"
            className="attach-file"
            onClick={() => fileInputRef.current?.click()}
            disabled={disabled}
            title="Attach file"
          >
            📎
          </button>

          <button
            type="button"
            className="send-message"
            onClick={handleSend}
            disabled={disabled || (!message.trim() && !file)}
            title="Send message (Enter)"
          >
            ➤
          </button>
        </div>
      </div>

      {/* Drag-and-drop overlay */}
      {isDragging && (
        <div className="drag-overlay">
          <div className="drag-message">📁 Drop file here to attach</div>
        </div>
      )}
    </div>
  );
};
```

### 4. Complete Chat View Component

```tsx
// src/pages/ChatView.tsx

import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { ChatAPI } from '../api/chat.service';
import { ChatMessages } from '../components/chat/ChatMessages';
import { ChatInput } from '../components/chat/ChatInput';
import { ModelSelector } from '../components/chat/ModelSelector';
import type { ChatDetail, ChatMessage, MessageResponse } from '../types/chat';

export const ChatView: React.FC = () => {
  const { chatId } = useParams<{ chatId: string }>();
  const [chat, setChat] = useState<ChatDetail | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (chatId) {
      loadChat();
    }
  }, [chatId]);

  const loadChat = async () => {
    if (!chatId) return;

    try {
      setLoading(true);
      const chatDetail = await ChatAPI.getChatDetail(chatId);
      setChat(chatDetail);
      setMessages(chatDetail.messages);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load chat');
    } finally {
      setLoading(false);
    }
  };

  const handleSendMessage = async (content: string, file?: File) => {
    if (!chatId || !content.trim()) return;

    try {
      setSending(true);

      // Добавить user сообщение в UI сразу (оптимистичное обновление)
      const userMessage: ChatMessage = {
        role: 'user',
        content: content.trim(),
        metadata: {},
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMessage]);

      // Отправить на backend
      let aiResponse: MessageResponse;
      if (file) {
        aiResponse = await ChatAPI.sendMessageWithFile(chatId, content, file);
      } else {
        aiResponse = await ChatAPI.sendMessage(chatId, content);
      }

      // Добавить AI ответ
      setMessages((prev) => [...prev, aiResponse]);

      // Обновить metadata чата
      if (chat) {
        setChat({
          ...chat,
          metadata: {
            ...chat.metadata,
            messages_count: messages.length + 2, // user + assistant
            tokens_used: chat.metadata.tokens_used + (aiResponse.metadata.tokens_used || 0),
            rag_queries_count: chat.metadata.rag_queries_count + (aiResponse.metadata.rag_chunks_used > 0 ? 1 : 0),
          },
        });
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send message');

      // Удалить оптимистично добавленное user сообщение при ошибке
      setMessages((prev) => prev.slice(0, -1));
    } finally {
      setSending(false);
    }
  };

  const handleSwitchModel = async (modelKey: string) => {
    if (!chatId) return;

    try {
      const updatedChat = await ChatAPI.switchModel(chatId, modelKey);
      setChat(updatedChat);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to switch model');
      throw err; // Re-throw для ModelSelector
    }
  };

  if (loading) {
    return <div className="chat-view loading">Loading chat...</div>;
  }

  if (error && !chat) {
    return (
      <div className="chat-view error">
        <h3>Error</h3>
        <p>{error}</p>
        <button onClick={loadChat}>Retry</button>
      </div>
    );
  }

  if (!chat) {
    return <div className="chat-view not-found">Chat not found</div>;
  }

  return (
    <div className="chat-view">
      <header className="chat-header">
        <div className="chat-info">
          <h2>{chat.title}</h2>
          <div className="chat-metadata">
            <span>💬 {chat.metadata.messages_count} messages</span>
            <span>🔢 {chat.metadata.tokens_used} tokens</span>
            {chat.metadata.rag_queries_count > 0 && (
              <span>📎 {chat.metadata.rag_queries_count} RAG queries</span>
            )}
          </div>
        </div>

        <ModelSelector
          currentModel={chat.model_key}
          onSwitch={handleSwitchModel}
          disabled={sending}
        />
      </header>

      {error && (
        <div className="error-banner">
          {error}
          <button onClick={() => setError(null)}>Dismiss</button>
        </div>
      )}

      <ChatMessages messages={messages} isLoading={sending} />

      <ChatInput
        onSendMessage={handleSendMessage}
        disabled={sending}
        placeholder={
          chat.document_service_ids.length > 0
            ? 'Ask about your documents...'
            : 'Type your message...'
        }
      />
    </div>
  );
};
```

## CSS Styles

### Complete Chat Styles

```css
/* src/styles/chat.css */

.chat-view {
  display: flex;
  flex-direction: column;
  height: 100vh;
  max-height: 100vh;
}

/* Header */
.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  border-bottom: 1px solid #e0e0e0;
  background: #fff;
}

.chat-info h2 {
  margin: 0 0 0.5rem 0;
  font-size: 1.5rem;
}

.chat-metadata {
  display: flex;
  gap: 1rem;
  font-size: 0.9rem;
  color: #666;
}

/* Messages */
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
  background: #f5f5f5;
}

.message {
  display: flex;
  gap: 0.75rem;
  margin-bottom: 1rem;
  animation: slideIn 0.2s ease-out;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.message-avatar {
  font-size: 2rem;
  flex-shrink: 0;
}

.message-content {
  flex: 1;
  background: #fff;
  padding: 1rem;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.message-user .message-content {
  background: #e3f2fd;
}

.message-assistant .message-content {
  background: #f5f5f5;
}

/* Markdown styles */
.message-content h1,
.message-content h2,
.message-content h3 {
  margin-top: 1rem;
  margin-bottom: 0.5rem;
}

.message-content code {
  background: #f0f0f0;
  padding: 0.2rem 0.4rem;
  border-radius: 3px;
  font-family: 'Fira Code', monospace;
  font-size: 0.9em;
}

.message-content pre {
  margin: 1rem 0;
  border-radius: 6px;
  overflow-x: auto;
}

/* Message metadata */
.message-metadata {
  display: flex;
  gap: 1rem;
  margin-top: 0.5rem;
  font-size: 0.85rem;
  color: #999;
  padding-top: 0.5rem;
  border-top: 1px solid #e0e0e0;
}

.rag-indicator {
  color: #4caf50;
  font-weight: 500;
}

/* Typing indicator */
.typing-indicator {
  display: flex;
  gap: 0.3rem;
}

.typing-indicator span {
  width: 8px;
  height: 8px;
  background: #999;
  border-radius: 50%;
  animation: typing 1.4s infinite;
}

.typing-indicator span:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-indicator span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes typing {
  0%,
  60%,
  100% {
    transform: translateY(0);
  }
  30% {
    transform: translateY(-10px);
  }
}

/* Input area */
.chat-input {
  position: relative;
  border-top: 1px solid #e0e0e0;
  background: #fff;
  padding: 1rem;
}

.chat-input.dragging {
  background: #e3f2fd;
  border-color: #2196f3;
}

.file-preview {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem;
  margin-bottom: 0.5rem;
  background: #f5f5f5;
  border-radius: 6px;
}

.file-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.file-size {
  color: #999;
  font-size: 0.9rem;
}

.remove-file {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: #999;
  transition: color 0.2s;
}

.remove-file:hover {
  color: #f44336;
}

.upload-progress {
  position: relative;
  height: 4px;
  background: #e0e0e0;
  border-radius: 2px;
  margin-bottom: 0.5rem;
  overflow: hidden;
}

.upload-progress-bar {
  height: 100%;
  background: #4caf50;
  transition: width 0.3s;
}

.upload-progress-text {
  position: absolute;
  top: -20px;
  right: 0;
  font-size: 0.75rem;
  color: #666;
}

.input-area {
  display: flex;
  gap: 0.5rem;
}

.input-area textarea {
  flex: 1;
  padding: 0.75rem;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  resize: none;
  font-family: inherit;
  font-size: 1rem;
}

.input-area textarea:focus {
  outline: none;
  border-color: #2196f3;
}

.input-actions {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.attach-file,
.send-message {
  width: 40px;
  height: 40px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 1.2rem;
  transition: all 0.2s;
}

.attach-file {
  background: #f5f5f5;
  color: #666;
}

.attach-file:hover {
  background: #e0e0e0;
}

.send-message {
  background: #2196f3;
  color: #fff;
}

.send-message:hover {
  background: #1976d2;
}

.send-message:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.drag-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(33, 150, 243, 0.1);
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px dashed #2196f3;
  border-radius: 6px;
}

.drag-message {
  font-size: 1.5rem;
  color: #2196f3;
  font-weight: 500;
}

/* Model selector */
.model-selector {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.model-selector label {
  font-weight: 500;
  color: #666;
}

.model-selector select {
  padding: 0.5rem 1rem;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  font-size: 1rem;
  cursor: pointer;
  background: #fff;
  transition: border-color 0.2s;
}

.model-selector select:focus {
  outline: none;
  border-color: #2196f3;
}

.model-selector select.switching {
  opacity: 0.6;
  cursor: wait;
}

.model-selector .spinner {
  font-size: 0.9rem;
  color: #999;
}

/* Error banner */
.error-banner {
  padding: 1rem;
  background: #ffebee;
  color: #c62828;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #ef9a9a;
}

.error-banner button {
  padding: 0.25rem 0.75rem;
  background: #c62828;
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

/* Loading states */
.chat-view.loading {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100vh;
  font-size: 1.5rem;
  color: #999;
}
```

## State Management (Optional: React Context)

### Chat Context Provider

```tsx
// src/context/ChatContext.tsx

import React, { createContext, useContext, useState, useCallback } from 'react';
import { ChatAPI } from '../api/chat.service';
import type { ChatListItem, ChatDetail, ModelInfo } from '../types/chat';

interface ChatContextValue {
  chats: ChatListItem[];
  models: ModelInfo[];
  loading: boolean;
  error: string | null;

  loadChats: () => Promise<void>;
  loadModels: () => Promise<void>;
  createChat: (params: {
    model_key: string;
    title: string;
    workspace_id?: string;
  }) => Promise<ChatDetail>;
  deleteChat: (chatId: string) => Promise<void>;
}

const ChatContext = createContext<ChatContextValue | undefined>(undefined);

export const ChatProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [chats, setChats] = useState<ChatListItem[]>([]);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadChats = useCallback(async () => {
    try {
      setLoading(true);
      const data = await ChatAPI.listChats();
      setChats(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load chats');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadModels = useCallback(async () => {
    try {
      const data = await ChatAPI.getModels();
      setModels(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load models');
    }
  }, []);

  const createChat = useCallback(async (params: {
    model_key: string;
    title: string;
    workspace_id?: string;
  }) => {
    const chat = await ChatAPI.createChat(params);
    await loadChats(); // Reload list
    return chat;
  }, [loadChats]);

  const deleteChat = useCallback(async (chatId: string) => {
    await ChatAPI.deleteChat(chatId);
    await loadChats(); // Reload list
  }, [loadChats]);

  return (
    <ChatContext.Provider
      value={{
        chats,
        models,
        loading,
        error,
        loadChats,
        loadModels,
        createChat,
        deleteChat,
      }}
    >
      {children}
    </ChatContext.Provider>
  );
};

export const useChatContext = () => {
  const context = useContext(ChatContext);
  if (!context) {
    throw new Error('useChatContext must be used within ChatProvider');
  }
  return context;
};
```

## Testing Examples

### Unit Test (Jest + React Testing Library)

```typescript
// src/components/chat/ChatInput.test.tsx

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ChatInput } from './ChatInput';

describe('ChatInput', () => {
  it('should send text message on Enter', async () => {
    const mockSend = jest.fn();
    render(<ChatInput onSendMessage={mockSend} />);

    const textarea = screen.getByPlaceholderText(/type your message/i);
    fireEvent.change(textarea, { target: { value: 'Test message' } });
    fireEvent.keyPress(textarea, { key: 'Enter', shiftKey: false });

    await waitFor(() => {
      expect(mockSend).toHaveBeenCalledWith('Test message', undefined);
    });
  });

  it('should handle file drop', async () => {
    const mockSend = jest.fn();
    render(<ChatInput onSendMessage={mockSend} />);

    const file = new File(['content'], 'test.pdf', { type: 'application/pdf' });
    const dropzone = screen.getByClassName('chat-input');

    fireEvent.drop(dropzone, { dataTransfer: { files: [file] } });

    expect(screen.getByText('test.pdf')).toBeInTheDocument();
  });
});
```

## Best Practices

### 1. Optimistic UI Updates
Добавляйте user сообщения в UI немедленно, не дожидаясь backend ответа. Откатывайте при ошибке.

### 2. Auto-scroll
Используйте `useRef` + `scrollIntoView` для автоматического скролла к последнему сообщению.

### 3. Markdown Safety
Используйте `ReactMarkdown` вместо `dangerouslySetInnerHTML` для безопасного рендеринга Markdown.

### 4. Code Highlighting
Интегрируйте `react-syntax-highlighter` для подсветки синтаксиса кодовых блоков.

### 5. Error Boundaries
Оборачивайте компоненты чата в `ErrorBoundary` для graceful error handling.

### 6. Debouncing
Для автосохранения черновиков используйте debounce (lodash.debounce).

### 7. WebSocket (Future)
Для real-time обновлений в team chats рассмотрите WebSocket вместо polling.

## 🎨 Floating Chat Widget Implementation

### Концепция и UI/UX

**Floating Widget Requirements:**
- Круглый виджет (60x60px) в правом нижнем углу (`position: fixed; bottom: 24px; right: 24px; z-index: 9999`)
- Иконка: message bubble или robot icon (можно анимированная при получении сообщений)
- При клике открывается чат-окно (400x600px), можно сделать draggable/resizable
- Чат остаётся открытым до явного закрытия пользователем
- Сохранение состояния (открыт/закрыт) в localStorage

### Component: FloatingChatWidget

```tsx
// src/components/chat/FloatingChatWidget.tsx

import React, { useState, useEffect } from 'react';
import { ChatAPI } from '../../api/chat.service';
import { ChatWindow } from './ChatWindow';
import { MessageCircle, X, Minimize2 } from 'lucide-react';
import type { ChatDetail } from '../../types/chat';
import './FloatingChatWidget.css';

interface FloatingChatWidgetProps {
  /** UUID текущего пользователя */
  userId: string;

  /** UUID workspace (null для персонального чата) */
  workspaceId?: string | null;
}

export const FloatingChatWidget: React.FC<FloatingChatWidgetProps> = ({
  userId,
  workspaceId = null,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  const [currentChat, setCurrentChat] = useState<ChatDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);

  // Восстановить состояние из localStorage
  useEffect(() => {
    const savedState = localStorage.getItem('chatWidgetState');
    if (savedState) {
      const { isOpen: savedIsOpen, chatId } = JSON.parse(savedState);
      setIsOpen(savedIsOpen);

      if (chatId) {
        loadChat(chatId);
      }
    }
  }, []);

  // Сохранить состояние в localStorage
  useEffect(() => {
    localStorage.setItem('chatWidgetState', JSON.stringify({
      isOpen,
      chatId: currentChat?.id || null,
    }));
  }, [isOpen, currentChat]);

  const loadChat = async (chatId: string) => {
    try {
      setLoading(true);
      const chat = await ChatAPI.getChatDetail(chatId);
      setCurrentChat(chat);
    } catch (error) {
      console.error('Failed to load chat:', error);
      // Создать новый чат при ошибке
      await createNewChat();
    } finally {
      setLoading(false);
    }
  };

  const createNewChat = async () => {
    try {
      setLoading(true);
      const newChat = await ChatAPI.createChat({
        model_key: 'qwen_coder',
        title: 'Quick Chat',
        workspace_id: workspaceId,
        document_service_ids: [],
      });
      setCurrentChat(newChat);
    } catch (error) {
      console.error('Failed to create chat:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleToggle = async () => {
    if (!isOpen && !currentChat) {
      await createNewChat();
    }
    setIsOpen(!isOpen);
    setIsMinimized(false);
  };

  const handleClose = () => {
    setIsOpen(false);
    setCurrentChat(null);
    localStorage.removeItem('chatWidgetState');
  };

  const handleMinimize = () => {
    setIsMinimized(!isMinimized);
  };

  return (
    <>
      {/* Floating Button */}
      {!isOpen && (
        <button
          className="floating-chat-button"
          onClick={handleToggle}
          aria-label="Open chat"
          title="Quick AI Chat"
        >
          <MessageCircle size={28} />
          {unreadCount > 0 && (
            <span className="unread-badge">{unreadCount}</span>
          )}
        </button>
      )}

      {/* Chat Window */}
      {isOpen && (
        <div className={`floating-chat-window ${isMinimized ? 'minimized' : ''}`}>
          {/* Header */}
          <div className="chat-window-header">
            <div className="header-title">
              <MessageCircle size={20} />
              <span>AI Assistant</span>
            </div>
            <div className="header-actions">
              <button
                onClick={handleMinimize}
                className="header-button"
                aria-label={isMinimized ? 'Restore' : 'Minimize'}
              >
                <Minimize2 size={18} />
              </button>
              <button
                onClick={handleClose}
                className="header-button"
                aria-label="Close chat"
              >
                <X size={18} />
              </button>
            </div>
          </div>

          {/* Content */}
          {!isMinimized && (
            <div className="chat-window-content">
              {loading ? (
                <div className="chat-loading">Loading chat...</div>
              ) : currentChat ? (
                <ChatWindow
                  chat={currentChat}
                  onChatUpdate={setCurrentChat}
                  compact={true}
                />
              ) : (
                <div className="chat-empty">
                  <p>Start a conversation</p>
                  <button onClick={createNewChat}>New Chat</button>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </>
  );
};
```

### CSS Styles

```css
/* src/components/chat/FloatingChatWidget.css */

/* Floating Button */
.floating-chat-button {
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 9999;
  width: 60px;
  height: 60px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.2s, box-shadow 0.2s;
}

.floating-chat-button:hover {
  transform: scale(1.05);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.2);
}

.floating-chat-button:active {
  transform: scale(0.95);
}

.unread-badge {
  position: absolute;
  top: -5px;
  right: -5px;
  background: #ef4444;
  color: white;
  font-size: 12px;
  font-weight: bold;
  padding: 2px 6px;
  border-radius: 10px;
  min-width: 20px;
  text-align: center;
}

/* Chat Window */
.floating-chat-window {
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 9998;
  width: 400px;
  height: 600px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  animation: slideUp 0.3s ease-out;
}

.floating-chat-window.minimized {
  height: 60px;
}

@keyframes slideUp {
  from {
    transform: translateY(20px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

/* Header */
.chat-window-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: 12px 12px 0 0;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  font-size: 16px;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.header-button {
  background: transparent;
  border: none;
  color: white;
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  transition: background 0.2s;
}

.header-button:hover {
  background: rgba(255, 255, 255, 0.2);
}

/* Content */
.chat-window-content {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.chat-loading,
.chat-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #6b7280;
}

.chat-empty button {
  margin-top: 16px;
  padding: 8px 16px;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
}

.chat-empty button:hover {
  background: #5568d3;
}

/* Responsive */
@media (max-width: 768px) {
  .floating-chat-window {
    width: calc(100vw - 32px);
    height: calc(100vh - 100px);
    bottom: 16px;
    right: 16px;
  }
}
```

### Document Selection Component

```tsx
// src/components/chat/DocumentSelector.tsx

import React, { useState, useEffect } from 'react';
import { FileText, CheckCircle, AlertCircle } from 'lucide-react';
import type { DocumentServiceListItem } from '../../types/document';

interface DocumentSelectorProps {
  /** Список выбранных document_service_ids */
  selectedDocuments: string[];

  /** Callback при изменении выбора */
  onSelectionChange: (documentIds: string[]) => void;

  /** UUID workspace для фильтрации (null = персональные) */
  workspaceId?: string | null;
}

export const DocumentSelector: React.FC<DocumentSelectorProps> = ({
  selectedDocuments,
  onSelectionChange,
  workspaceId = null,
}) => {
  const [documents, setDocuments] = useState<DocumentServiceListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadDocuments();
  }, [workspaceId]);

  const loadDocuments = async () => {
    try {
      setLoading(true);
      // Загрузить документы через API
      const response = await fetch('/api/v1/document-services', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('accessToken')}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to load documents');
      }

      const data = await response.json();
      setDocuments(data.data || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const toggleDocument = (documentId: string) => {
    const newSelection = selectedDocuments.includes(documentId)
      ? selectedDocuments.filter(id => id !== documentId)
      : [...selectedDocuments, documentId];

    onSelectionChange(newSelection);
  };

  const canUseDocument = (doc: DocumentServiceListItem): boolean => {
    // Проверка: включена ли функция view_pdf (RAG готов)
    return doc.functions?.view_pdf === true;
  };

  if (loading) {
    return <div className="document-selector loading">Loading documents...</div>;
  }

  if (error) {
    return (
      <div className="document-selector error">
        <AlertCircle size={20} />
        <span>{error}</span>
        <button onClick={loadDocuments}>Retry</button>
      </div>
    );
  }

  return (
    <div className="document-selector">
      <h3>Select Documents for Context</h3>
      <div className="document-list">
        {documents.map((doc) => {
          const isSelected = selectedDocuments.includes(doc.id);
          const isReady = canUseDocument(doc);

          return (
            <div
              key={doc.id}
              className={`document-item ${isSelected ? 'selected' : ''} ${!isReady ? 'disabled' : ''}`}
              onClick={() => isReady && toggleDocument(doc.id)}
            >
              <div className="document-icon">
                <FileText size={20} />
                {isSelected && <CheckCircle size={16} className="check-icon" />}
              </div>

              <div className="document-info">
                <div className="document-title">{doc.title}</div>
                <div className="document-meta">
                  {doc.file_size && `${(doc.file_size / 1024 / 1024).toFixed(2)} MB`}
                  {!isReady && (
                    <span className="warning">
                      <AlertCircle size={14} />
                      Enable "View PDF" to use in chat
                    </span>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {selectedDocuments.length > 0 && (
        <div className="selection-summary">
          {selectedDocuments.length} document(s) selected
        </div>
      )}
    </div>
  );
};
```

### Integration with Chat Window

```tsx
// src/components/chat/ChatWindow.tsx

import React, { useState } from 'react';
import { ChatMessages } from './ChatMessages';
import { ChatInput } from './ChatInput';
import { ModelSelector } from './ModelSelector';
import { DocumentSelector } from './DocumentSelector';
import { Settings, FileText } from 'lucide-react';
import type { ChatDetail } from '../../types/chat';

interface ChatWindowProps {
  chat: ChatDetail;
  onChatUpdate: (chat: ChatDetail) => void;
  compact?: boolean;
}

export const ChatWindow: React.FC<ChatWindowProps> = ({
  chat,
  onChatUpdate,
  compact = false,
}) => {
  const [showDocuments, setShowDocuments] = useState(false);
  const [showSettings, setShowSettings] = useState(false);

  const handleDocumentsChange = async (documentIds: string[]) => {
    try {
      // Обновить document_service_ids через API
      const response = await fetch(`/api/v1/chat/${chat.chat_id}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('accessToken')}`,
        },
        body: JSON.stringify({ document_service_ids: documentIds }),
      });

      if (!response.ok) {
        throw new Error('Failed to update documents');
      }

      const data = await response.json();
      onChatUpdate(data.data);
    } catch (error) {
      console.error('Failed to update documents:', error);
    }
  };

  return (
    <div className={`chat-window ${compact ? 'compact' : ''}`}>
      {/* Toolbar */}
      <div className="chat-toolbar">
        <button
          onClick={() => setShowDocuments(!showDocuments)}
          className={`toolbar-button ${showDocuments ? 'active' : ''}`}
          title="Select documents"
        >
          <FileText size={18} />
          {chat.document_service_ids.length > 0 && (
            <span className="badge">{chat.document_service_ids.length}</span>
          )}
        </button>

        <button
          onClick={() => setShowSettings(!showSettings)}
          className={`toolbar-button ${showSettings ? 'active' : ''}`}
          title="Chat settings"
        >
          <Settings size={18} />
        </button>
      </div>

      {/* Document Selector Panel */}
      {showDocuments && (
        <div className="chat-panel">
          <DocumentSelector
            selectedDocuments={chat.document_service_ids}
            onSelectionChange={handleDocumentsChange}
            workspaceId={chat.workspace_id}
          />
        </div>
      )}

      {/* Settings Panel */}
      {showSettings && (
        <div className="chat-panel">
          <ModelSelector
            currentModel={chat.model_key}
            onSwitch={async (modelKey) => {
              // Переключить модель через API
              const response = await ChatAPI.switchModel(chat.chat_id, modelKey);
              onChatUpdate(response);
            }}
          />
        </div>
      )}

      {/* Messages */}
      <ChatMessages messages={chat.messages} />

      {/* Input */}
      <ChatInput
        onSendMessage={async (content, file) => {
          // Отправить сообщение и обновить чат
          const response = file
            ? await ChatAPI.sendMessageWithFile(chat.chat_id, content, file)
            : await ChatAPI.sendMessage(chat.chat_id, content);

          onChatUpdate({
            ...chat,
            messages: [...chat.messages, response],
          });
        }}
        disabled={false}
      />
    </div>
  );
};
```

### Backend Integration Checklist

**Для полной работы Floating Chat нужно убедиться:**

1. ✅ **Chat API работает**: `POST /api/v1/chat`, `GET /api/v1/chat/{id}`, `POST /api/v1/chat/{id}/message`
2. ✅ **Document Services API**: `GET /api/v1/document-services` (с фильтрацией по `is_public` и `author_id`)
3. ✅ **RAG Integration**: При отправке сообщения backend автоматически использует `document_service_ids` из чата
4. ✅ **Function Check**: Фронтенд проверяет `functions.view_pdf === true` перед добавлением документа
5. ⏳ **Future: Drag-and-drop Upload**: Прямая загрузка файлов в чат (создание DocumentService + добавление в chat)
6. ⏳ **Future: Auto-RAG Processing**: При загрузке PDF автоматически включать `view_pdf=true` и запускать обработку

### Usage Example

```tsx
// src/App.tsx

import React from 'react';
import { FloatingChatWidget } from './components/chat/FloatingChatWidget';
import { useAuth } from './hooks/useAuth';

export const App: React.FC = () => {
  const { user, workspace } = useAuth();

  return (
    <div className="app">
      {/* Your main app content */}
      <main>
        {/* ... */}
      </main>

      {/* Floating Chat Widget */}
      {user && (
        <FloatingChatWidget
          userId={user.id}
          workspaceId={workspace?.id || null}
        />
      )}
    </div>
  );
};
```

## Environment Variables

```env
# .env.local

REACT_APP_API_URL=http://localhost:8000/api/v1
REACT_APP_WS_URL=ws://localhost:8000/ws
REACT_APP_MAX_FILE_SIZE=52428800
```

## Next Steps

1. **Authentication**: Интегрируйте JWT login/refresh flow
2. **Chat List**: Создайте компонент списка чатов с пагинацией
3. **Workspace Selector**: Добавьте выбор workspace при создании чата
4. **Document Browser**: Интегрируйте выбор документов из DocumentService ✅ **DONE**
5. **Settings Panel**: UI для изменения temperature/max_tokens
6. **Export Chat**: Кнопка экспорта истории в PDF/Markdown
7. **Voice Input**: Добавьте Speech-to-Text для голосового ввода
8. **Drag-and-drop Upload**: Прямая загрузка файлов в чат с автоматическим RAG
9. **Floating Widget**: Реализовать круглый виджет в правом нижнем углу ✅ **DONE**
10. **Document RAG Auto-processing**: Автоматическая обработка PDF при активации `view_pdf`

Полный API reference: `RAG_CHAT_FREE_MODELS.md`
