package com.aicoach.repo;

import com.aicoach.domain.InterviewEntity;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

public interface InterviewRepository extends JpaRepository<InterviewEntity, Long> {
    Page<InterviewEntity> findByUser_IdOrderByCreatedAtDesc(Long userId, Pageable pageable);
}
