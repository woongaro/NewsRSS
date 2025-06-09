// 전역 변수
let isLoading = false;

// DOM 요소들
const searchForm = document.getElementById('searchForm');
const searchInput = document.getElementById('searchInput');
const loadingSpinner = document.getElementById('loadingSpinner');
const searchInfo = document.getElementById('searchInfo');
const searchQuery = document.getElementById('searchQuery');
const newsCount = document.getElementById('newsCount');
const newsList = document.getElementById('newsList');
const errorContainer = document.getElementById('errorContainer');
const errorMessage = document.getElementById('errorMessage');

// 페이지 로드 시 초기 검색 실행
document.addEventListener('DOMContentLoaded', function() {
    performSearch('부정선거');
});

// 검색 폼 이벤트 리스너
searchForm.addEventListener('submit', function(e) {
    e.preventDefault();
    const query = searchInput.value.trim();
    if (query && !isLoading) {
        performSearch(query);
    }
});

// 검색 수행 함수
async function performSearch(query) {
    if (isLoading) return;
    
    isLoading = true;
    showLoading();
    hideError();
    hideSearchInfo();
    clearNewsList();
    
    try {
        const response = await fetch(`/api/news?q=${encodeURIComponent(query)}`);
        const data = await response.json();
        
        if (data.status === 'success') {
            displayNews(data.news, data.query, data.count);
        } else {
            showError(data.message || '뉴스를 가져오는 중 오류가 발생했습니다.');
        }
    } catch (error) {
        console.error('Error fetching news:', error);
        showError('네트워크 오류가 발생했습니다. 인터넷 연결을 확인해주세요.');
    } finally {
        isLoading = false;
        hideLoading();
    }
}

// 뉴스 목록 표시 함수
function displayNews(newsItems, query, count) {
    // 검색 정보 표시
    searchQuery.textContent = query;
    newsCount.textContent = count;
    showSearchInfo();
    
    // 뉴스가 없는 경우
    if (newsItems.length === 0) {
        showError('검색 결과가 없습니다. 다른 키워드로 검색해보세요.');
        return;
    }
    
    // 뉴스 항목들 생성
    newsItems.forEach((news, index) => {
        const newsCard = createNewsCard(news, index);
        newsList.appendChild(newsCard);
    });
    
    // 스크롤을 뉴스 목록으로 이동
    setTimeout(() => {
        document.getElementById('newsContainer').scrollIntoView({
            behavior: 'smooth',
            block: 'start'
        });
    }, 100);
}

// 뉴스 카드 생성 함수
function createNewsCard(news, index) {
    const col = document.createElement('div');
    col.className = 'col-12';
    
    // 애니메이션 지연 설정
    const animationDelay = index * 0.1;
    
    // 이미지 HTML 생성
    const imageHtml = news.image ? `
        <div class="news-image-container">
            <img src="${escapeHtml(news.image)}" 
                 alt="${escapeHtml(news.title)}" 
                 class="news-image"
                 onerror="this.style.display='none';"
                 loading="lazy">
        </div>
    ` : '';
    
    col.innerHTML = `
        <div class="news-card" style="animation-delay: ${animationDelay}s">
            ${imageHtml}
            <div class="news-content">
                <a href="${news.link}" target="_blank" rel="noopener" class="news-title">
                    ${escapeHtml(news.title)}
                </a>
                <div class="news-meta">
                    <i class="fas fa-clock me-1"></i>
                    ${formatDate(news.published)}
                    ${news.source ? `<span class="ms-2"><i class="fas fa-newspaper me-1"></i>${escapeHtml(news.source)}</span>` : ''}
                </div>
                ${news.summary ? `<div class="news-summary">${escapeHtml(stripHtmlTags(news.summary))}</div>` : ''}
            </div>
        </div>
    `;
    
    return col;
}

// 날짜 포맷팅 함수
function formatDate(dateString) {
    if (!dateString) return '날짜 정보 없음';
    
    try {
        const date = new Date(dateString);
        const now = new Date();
        const diffTime = Math.abs(now - date);
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
        
        if (diffDays === 1) {
            return '하루 전';
        } else if (diffDays < 7) {
            return `${diffDays}일 전`;
        } else {
            return date.toLocaleDateString('ko-KR', {
                year: 'numeric',
                month: 'long',
                day: 'numeric'
            });
        }
    } catch (error) {
        return '날짜 정보 없음';
    }
}

// HTML 태그 제거 함수
function stripHtmlTags(html) {
    const div = document.createElement('div');
    div.innerHTML = html;
    return div.textContent || div.innerText || '';
}

// HTML 이스케이프 함수
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// UI 상태 관리 함수들
function showLoading() {
    loadingSpinner.classList.remove('d-none');
}

function hideLoading() {
    loadingSpinner.classList.add('d-none');
}

function showSearchInfo() {
    searchInfo.classList.remove('d-none');
}

function hideSearchInfo() {
    searchInfo.classList.add('d-none');
}

function showError(message) {
    errorMessage.textContent = message;
    errorContainer.classList.remove('d-none');
}

function hideError() {
    errorContainer.classList.add('d-none');
}

function clearNewsList() {
    newsList.innerHTML = '';
}

// 키보드 단축키 지원
document.addEventListener('keydown', function(e) {
    // Ctrl+K 또는 Cmd+K로 검색 입력에 포커스
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        searchInput.focus();
        searchInput.select();
    }
});

// 검색 입력 플레이스홀더 효과
const placeholders = [
    '검색할 키워드를 입력하세요...',
    '예: 정치, 경제, 사회, 국제',
    '예: 코로나, 주식, 부동산',
    '예: 스포츠, 문화, 과학기술'
];

let placeholderIndex = 0;
setInterval(() => {
    if (!searchInput.matches(':focus')) {
        searchInput.placeholder = placeholders[placeholderIndex];
        placeholderIndex = (placeholderIndex + 1) % placeholders.length;
    }
}, 3000); 