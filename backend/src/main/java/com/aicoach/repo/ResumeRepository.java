package com.aicoach.repo;

import com.aicoach.domain.ResumeEntity;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ResumeRepository extends JpaRepository<ResumeEntity, Long> {
    Page<ResumeEntity> findByUser_IdOrderByCreatedAtDesc(Long userId, Pageable pageable);
}
