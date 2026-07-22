<template>
  <Teleport to="body">
    <div class="modal-overlay" v-if="visible" @click.self="$emit('close')">
      <div class="modal-content">
        <!-- Header -->
        <div class="modal-header">
          <h3>{{ isEdit ? '编辑评价' : '写评价' }}</h3>
          <button class="modal-close" @click="$emit('close')">✕</button>
        </div>

        <!-- Body -->
        <div class="modal-body">
          <!-- User Name -->
          <div class="form-group">
            <label class="form-label" for="review-username">昵称</label>
            <input
              id="review-username"
              v-model="formUserName"
              class="form-input"
              type="text"
              placeholder="你的昵称"
              maxlength="50"
            />
          </div>

          <!-- Star Rating -->
          <div class="form-group">
            <label class="form-label">评分</label>
            <div class="star-picker">
              <button
                v-for="i in 5"
                :key="i"
                class="star-btn"
                :class="{ active: i <= formRating }"
                @click="formRating = i"
                @mouseenter="hoverRating = i"
                @mouseleave="hoverRating = 0"
                type="button"
              >
                {{ (hoverRating || formRating) >= i ? '★' : '☆' }}
              </button>
              <span class="rating-hint">{{ ratingHint }}</span>
            </div>
          </div>

          <!-- Review Text -->
          <div class="form-group">
            <label class="form-label" for="review-text">评价内容</label>
            <textarea
              id="review-text"
              v-model="formText"
              class="form-textarea"
              :placeholder="isEdit ? '修改你的评价...' : '分享你的用餐体验...'"
              rows="4"
              maxlength="2000"
            ></textarea>
            <span class="char-count">{{ formText.length }}/2000</span>
          </div>

          <!-- Error -->
          <div class="form-error" v-if="errorMsg">
            <span class="error-text">{{ errorMsg }}</span>
          </div>

          <!-- Actions -->
          <div class="form-actions">
            <button
              class="btn-submit"
              :disabled="submitting || !canSubmit"
              @click="handleSubmit"
            >
              <span class="loading-spinner-sm" v-if="submitting"></span>
              <span>{{ isEdit ? '保存修改' : '发布评价' }}</span>
            </button>

            <button
              v-if="isEdit"
              class="btn-delete"
              :disabled="deleting"
              @click="handleDelete"
            >
              <span v-if="deleting">删除中...</span>
              <span v-else>删除评价</span>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Delete Confirmation Overlay -->
    <div class="modal-overlay" v-if="showDeleteConfirm" @click.self="showDeleteConfirm = false">
      <div class="modal-content confirm-dialog">
        <div class="modal-header">
          <h3>确认删除</h3>
        </div>
        <div class="modal-body">
          <p class="confirm-text">确定要删除这条评价吗？此操作不可撤销。</p>
          <div class="form-actions">
            <button class="btn-submit delete-confirm" @click="confirmDelete">确认删除</button>
            <button class="btn-cancel" @click="showDeleteConfirm = false">取消</button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script>
import { ref, computed, watch } from 'vue'
import { createReview, updateReview, deleteReview } from '../api/modules/reviews.js'

export default {
  name: 'ReviewForm',
  props: {
    businessId: { type: String, required: true },
    visible: { type: Boolean, default: false },
    initialReview: {
      type: Object,
      default: null,
      // { review_id: string, rating: number, text: string }
    },
  },
  emits: ['close', 'saved', 'deleted'],

  setup(props, { emit }) {
    const formRating = ref(0)
    const formText = ref('')
    const formUserName = ref('')
    const hoverRating = ref(0)
    const submitting = ref(false)
    const deleting = ref(false)
    const errorMsg = ref('')
    const showDeleteConfirm = ref(false)

    const isEdit = computed(() => !!props.initialReview?.review_id)

    const canSubmit = computed(() =>
      formRating.value >= 1 && formText.value.trim().length > 0 && formUserName.value.trim().length > 0
    )

    const ratingHint = computed(() => {
      const r = hoverRating.value || formRating.value
      const hints = ['点击评分', '非常差', '较差', '一般', '不错', '太棒了']
      return hints[r] || ''
    })

    // Reset form when modal opens or initialReview changes
    watch(() => props.visible, (val) => {
      if (val) {
        errorMsg.value = ''
        showDeleteConfirm.value = false
        if (props.initialReview) {
          formRating.value = props.initialReview.rating || 0
          formText.value = props.initialReview.text || ''
          formUserName.value = props.initialReview.user_name || ''
        } else {
          formRating.value = 0
          formText.value = ''
          formUserName.value = ''
        }
      }
    })

    async function handleSubmit() {
      if (!canSubmit.value || submitting.value) return

      errorMsg.value = ''
      submitting.value = true

      try {
        if (isEdit.value) {
          const fields = {}
          if (formRating.value !== props.initialReview.rating) fields.rating = formRating.value
          if (formText.value.trim() !== (props.initialReview.text || '')) fields.text = formText.value.trim()

          if (Object.keys(fields).length === 0) {
            emit('close')
            return
          }
          await updateReview(props.initialReview.review_id, fields)
        } else {
          await createReview(props.businessId, {
            user_name: formUserName.value.trim(),
            rating: formRating.value,
            text: formText.value.trim(),
          })
        }
        emit('saved')
        emit('close')
      } catch (err) {
        errorMsg.value = err.message || '操作失败，请稍后重试'
      } finally {
        submitting.value = false
      }
    }

    function handleDelete() {
      showDeleteConfirm.value = true
    }

    async function confirmDelete() {
      if (deleting.value) return
      deleting.value = true
      errorMsg.value = ''

      try {
        await deleteReview(props.initialReview.review_id)
        showDeleteConfirm.value = false
        emit('deleted')
        emit('close')
      } catch (err) {
        errorMsg.value = err.message || '删除失败，请稍后重试'
        showDeleteConfirm.value = false
      } finally {
        deleting.value = false
      }
    }

    return {
      formRating, formText, formUserName, hoverRating,
      submitting, deleting, errorMsg,
      isEdit, canSubmit, ratingHint,
      showDeleteConfirm,
      handleSubmit, handleDelete, confirmDelete,
    }
  },
}
</script>

<style scoped>
/* ── Modal Overlay ── */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(26, 26, 46, 0.5);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: flex-end;
  justify-content: center;
  z-index: 200;
  animation: fadeIn 0.2s ease;
}
@media (min-width: 768px) {
  .modal-overlay {
    align-items: center;
    padding: var(--space-4);
  }
}

.modal-content {
  background: var(--card-bg);
  border-radius: var(--radius-xl) var(--radius-xl) 0 0;
  max-width: 480px;
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: var(--shadow-xl);
  animation: slideUp 0.3s var(--ease-spring);
}
@media (min-width: 768px) {
  .modal-content {
    border-radius: var(--radius-xl);
    max-height: 80vh;
  }
}

@keyframes slideUp {
  from { transform: translateY(100%); }
  to { transform: translateY(0); }
}

.confirm-dialog {
  border-radius: var(--radius-xl);
  max-width: 360px;
}

/* ── Header ── */
.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-4) var(--space-4);
  border-bottom: 1px solid var(--border);
  position: sticky;
  top: 0;
  background: var(--card-bg);
  z-index: 1;
}
.modal-header h3 {
  font-family: var(--font-display);
  font-size: var(--text-md);
  font-weight: 700;
}
.modal-close {
  width: 2rem;
  height: 2rem;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--warm-bg);
  font-size: var(--text-sm);
  color: var(--ink-muted);
  transition: background var(--duration-fast);
}
.modal-close:hover { background: var(--border); }

/* ── Body ── */
.modal-body {
  padding: var(--space-4);
}

/* ── Form Groups ── */
.form-group {
  margin-bottom: var(--space-5);
}
.form-label {
  display: block;
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--ink);
  margin-bottom: var(--space-2);
}

/* ── Star Picker ── */
.star-picker {
  display: flex;
  align-items: center;
  gap: var(--space-1);
}
.star-btn {
  font-size: 2rem;
  color: #DDD;
  transition: color var(--duration-fast), transform var(--duration-fast);
  padding: 0;
  line-height: 1;
  cursor: pointer;
}
.star-btn.active {
  color: var(--amber);
}
.star-btn:hover {
  transform: scale(1.15);
}
.rating-hint {
  margin-left: var(--space-3);
  font-size: var(--text-sm);
  color: var(--ink-muted);
  font-weight: 500;
}

/* ── Textarea ── */
.form-input {
  width: 100%;
  padding: var(--space-3);
  border: 1.5px solid var(--border);
  border-radius: var(--radius-md);
  font-family: var(--font-body);
  font-size: var(--text-base);
  color: var(--ink);
  background: var(--warm-bg);
  transition: border-color var(--duration-fast);
}
.form-input:focus {
  outline: none;
  border-color: var(--coral);
  background: var(--card-bg);
}
.form-input::placeholder {
  color: var(--ink-muted);
}

.form-textarea {
  width: 100%;
  padding: var(--space-3);
  border: 1.5px solid var(--border);
  border-radius: var(--radius-md);
  font-family: var(--font-body);
  font-size: var(--text-base);
  color: var(--ink);
  line-height: var(--leading-relaxed);
  resize: vertical;
  min-height: 100px;
  background: var(--warm-bg);
  transition: border-color var(--duration-fast);
}
.form-textarea:focus {
  outline: none;
  border-color: var(--coral);
  background: var(--card-bg);
}
.form-textarea::placeholder {
  color: var(--ink-muted);
}
.char-count {
  display: block;
  text-align: right;
  font-size: var(--text-xs);
  color: var(--ink-muted);
  margin-top: var(--space-1);
}

/* ── Error ── */
.form-error {
  padding: var(--space-2) var(--space-3);
  background: var(--sentiment-negative-bg);
  border-radius: var(--radius-sm);
  margin-bottom: var(--space-3);
}
.error-text {
  font-size: var(--text-sm);
  color: var(--sentiment-negative);
}

/* ── Actions ── */
.form-actions {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding-top: var(--space-2);
}

.btn-submit {
  width: 100%;
  padding: var(--space-3) var(--space-4);
  background: var(--coral);
  color: #fff;
  border-radius: var(--radius-full);
  font-size: var(--text-md);
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  transition: background var(--duration-fast), transform var(--duration-fast);
}
.btn-submit:hover:not(:disabled) { background: var(--coral-deep); }
.btn-submit:active:not(:disabled) { transform: scale(0.97); }
.btn-submit:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.btn-submit.delete-confirm {
  background: var(--sentiment-negative);
}
.btn-submit.delete-confirm:hover:not(:disabled) {
  background: #DC2626;
}

.btn-delete {
  width: 100%;
  padding: var(--space-2) var(--space-4);
  background: transparent;
  color: var(--sentiment-negative);
  border: 1px solid var(--sentiment-negative);
  border-radius: var(--radius-full);
  font-size: var(--text-sm);
  font-weight: 500;
  transition: background var(--duration-fast), color var(--duration-fast);
}
.btn-delete:hover:not(:disabled) {
  background: var(--sentiment-negative-bg);
}
.btn-delete:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-cancel {
  width: 100%;
  padding: var(--space-2) var(--space-4);
  background: var(--warm-bg);
  color: var(--ink-light);
  border: 1px solid var(--border);
  border-radius: var(--radius-full);
  font-size: var(--text-sm);
  font-weight: 500;
  transition: background var(--duration-fast);
}
.btn-cancel:hover {
  background: var(--border);
}

.confirm-text {
  font-size: var(--text-base);
  color: var(--ink-light);
  line-height: var(--leading-relaxed);
  margin-bottom: var(--space-4);
}

/* ── Loading Spinner (small) ── */
.loading-spinner-sm {
  width: 18px;
  height: 18px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  flex-shrink: 0;
}
@keyframes spin { to { transform: rotate(360deg); } }
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
</style>
