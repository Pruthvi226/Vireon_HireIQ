package com.aicoach.repo;

import com.aicoach.domain.QuestionEntity;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface QuestionRepository extends JpaRepository<QuestionEntity, Long> {
    List<QuestionEntity> findByInterview_IdOrderByCreatedAtAsc(Long interviewId);
}
