package com.aicoach.repo;

import com.aicoach.domain.FeedbackEntity;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface FeedbackRepository extends JpaRepository<FeedbackEntity, Long> {
    Optional<FeedbackEntity> findByInterview_Id(Long interviewId);
}
